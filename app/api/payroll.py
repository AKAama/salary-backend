from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from typing import List, Optional
from app.core.database import get_db
from app.models.models import User, Payroll, PayrollItem, PayrollItemDetail, Employee, SalaryRecord, SalaryItem
from app.schemas.schemas import (
    PayrollResponse, PayrollCreate, PayrollListResponse,
    PayrollItemResponse, PayrollItemCreate, PayrollItemDetailResponse
)
from app.api.deps import get_current_user
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/payrolls", tags=["工资单"])


def calculate_tax(gross_salary: Decimal) -> Decimal:
    """计算个人所得税 (简化版)"""
    # 免税额 5000 元
    taxable = gross_salary - Decimal("5000")
    if taxable <= 0:
        return Decimal("0")

    # 简化税率表
    if taxable <= 3000:
        tax = taxable * Decimal("0.03") - Decimal("0")
    elif taxable <= 12000:
        tax = taxable * Decimal("0.10") - Decimal("210")
    elif taxable <= 25000:
        tax = taxable * Decimal("0.20") - Decimal("1410")
    elif taxable <= 35000:
        tax = taxable * Decimal("0.25") - Decimal("2660")
    elif taxable <= 55000:
        tax = taxable * Decimal("0.30") - Decimal("4410")
    elif taxable <= 80000:
        tax = taxable * Decimal("0.35") - Decimal("7160")
    else:
        tax = taxable * Decimal("0.45") - Decimal("15160")

    return max(tax, Decimal("0"))


@router.get("", response_model=PayrollListResponse)
async def list_payrolls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    month: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取工资单列表"""
    query = select(Payroll).where(Payroll.tenant_id == current_user.tenant_id)

    if month:
        query = query.where(Payroll.month == month)
    if status:
        query = query.where(Payroll.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Payroll.created_at.desc())
    result = await db.execute(query)
    payrolls = result.scalars().all()

    return PayrollListResponse(
        total=total,
        items=[PayrollResponse.model_validate(p) for p in payrolls]
    )


@router.get("/{payroll_id}", response_model=PayrollResponse)
async def get_payroll(
    payroll_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取工资单详情"""
    result = await db.execute(
        select(Payroll).where(
            Payroll.id == payroll_id,
            Payroll.tenant_id == current_user.tenant_id
        )
    )
    payroll = result.scalar_one_or_none()
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found"
        )
    return PayrollResponse.model_validate(payroll)


@router.post("/generate", response_model=PayrollResponse)
async def generate_payroll(
    month: str,
    department_ids: Optional[List[int]] = None,
    remark: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """生成工资单"""
    # Check if payroll for this month already exists
    result = await db.execute(
        select(Payroll).where(
            Payroll.tenant_id == current_user.tenant_id,
            Payroll.month == month
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payroll for {month} already exists"
        )

    # Get employees
    query = select(Employee).where(
        Employee.tenant_id == current_user.tenant_id,
        Employee.status == True
    )
    if department_ids:
        query = query.where(Employee.department_id.in_(department_ids))

    result = await db.execute(query)
    employees = result.scalars().all()

    if not employees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No employees found"
        )

    # Create payroll
    payroll = Payroll(
        tenant_id=current_user.tenant_id,
        month=month,
        status="generated",
        remark=remark,
        created_by=current_user.id,
    )
    db.add(payroll)
    await db.flush()

    total_amount = Decimal("0")
    total_count = 0

    # Calculate salary for each employee
    for employee in employees:
        # Get salary records for this employee
        result = await db.execute(
            select(SalaryRecord).where(
                SalaryRecord.employee_id == employee.id
            )
        )
        salary_records = result.scalars().all()

        if not salary_records:
            continue

        # Calculate gross salary (taxable items only)
        gross_salary = Decimal("0")
        for record in salary_records:
            if record.salary_item and record.salary_item.is_taxable:
                gross_salary += record.amount
            # Add non-taxable items to net salary later
            # For now just track all
            gross_salary += record.amount

        # Calculate tax
        tax_amount = calculate_tax(gross_salary)

        # Net salary = gross - tax
        net_salary = gross_salary - tax_amount

        if net_salary <= 0:
            continue

        # Create payroll item
        payroll_item = PayrollItem(
            payroll_id=payroll.id,
            employee_id=employee.id,
            gross_salary=gross_salary,
            net_salary=net_salary,
            tax_amount=tax_amount,
            status="pending",
        )
        db.add(payroll_item)
        await db.flush()

        # Create payroll item details
        for record in salary_records:
            detail = PayrollItemDetail(
                payroll_item_id=payroll_item.id,
                salary_item_id=record.salary_item_id,
                salary_item_name=record.salary_item.name if record.salary_item else "未知",
                amount=record.amount,
                is_taxable=record.salary_item.is_taxable if record.salary_item else True,
            )
            db.add(detail)

        total_amount += net_salary
        total_count += 1

    # Update payroll totals
    payroll.total_amount = total_amount
    payroll.total_count = total_count

    await db.commit()
    await db.refresh(payroll)
    return PayrollResponse.model_validate(payroll)


@router.post("/{payroll_id}/pay")
async def pay_payroll(
    payroll_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """一键发薪"""
    # Get payroll
    result = await db.execute(
        select(Payroll).where(
            Payroll.id == payroll_id,
            Payroll.tenant_id == current_user.tenant_id
        )
    )
    payroll = result.scalar_one_or_none()
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found"
        )

    if payroll.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payroll already paid"
        )

    # Get payroll items
    result = await db.execute(
        select(PayrollItem).where(PayrollItem.payroll_id == payroll.id)
    )
    payroll_items = result.scalars().all()

    # TODO: Call WeChat Pay API
    # For now, just mark as paid
    paid_count = 0
    failed_count = 0

    for item in payroll_items:
        # Check if employee has wechat info
        result = await db.execute(
            select(Employee).where(Employee.id == item.employee_id)
        )
        employee = result.scalar_one_or_none()

        if not employee or not employee.wechat_openid:
            item.status = "failed"
            failed_count += 1
            continue

        # TODO: Actually call WeChat Pay transfer API
        # For now simulate success
        item.status = "paid"
        paid_count += 1

    payroll.status = "paid"
    await db.commit()

    return {
        "id": payroll.id,
        "month": payroll.month,
        "total_amount": payroll.total_amount,
        "total_count": payroll.total_count,
        "status": payroll.status,
        "paid_count": paid_count,
        "failed_count": failed_count
    }


@router.delete("/{payroll_id}")
async def delete_payroll(
    payroll_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除工资单"""
    result = await db.execute(
        select(Payroll).where(
            Payroll.id == payroll_id,
            Payroll.tenant_id == current_user.tenant_id
        )
    )
    payroll = result.scalar_one_or_none()
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found"
        )

    if payroll.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete paid payroll"
        )

    # Delete payroll items and details
    result = await db.execute(
        select(PayrollItem).where(PayrollItem.payroll_id == payroll.id)
    )
    items = result.scalars().all()

    for item in items:
        await db.execute(
            delete(PayrollItemDetail).where(PayrollItemDetail.payroll_item_id == item.id)
        )

    await db.execute(
        delete(PayrollItem).where(PayrollItem.payroll_id == payroll.id)
    )

    await db.delete(payroll)
    await db.commit()
    return {"message": "Payroll deleted successfully"}
