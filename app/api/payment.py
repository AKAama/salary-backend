from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.core.database import get_db
from app.models.models import User, PaymentRecord, PayrollItem, Employee
from app.schemas.schemas import (
    PaymentRecordResponse, PaymentListResponse
)
from app.api.deps import get_current_user
from datetime import datetime

router = APIRouter(prefix="/payments", tags=["发薪记录"])


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    payroll_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取发薪记录列表"""
    query = select(PaymentRecord).join(PayrollItem).join(Employee).where(
        Employee.tenant_id == current_user.tenant_id
    )

    if payroll_id:
        query = query.where(PayrollItem.payroll_id == payroll_id)
    if status:
        query = query.where(PaymentRecord.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(PaymentRecord.created_at.desc())
    result = await db.execute(query)
    payments = result.scalars().all()

    return PaymentListResponse(
        total=total,
        items=[PaymentRecordResponse.model_validate(p) for p in payments]
    )


@router.get("/{payment_id}", response_model=PaymentRecordResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取发薪记录详情"""
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found"
        )

    # Verify tenant
    result = await db.execute(
        select(PayrollItem).where(PayrollItem.id == payment.payroll_item_id)
    )
    payroll_item = result.scalar_one_or_none()
    if not payroll_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll item not found"
        )

    result = await db.execute(
        select(Employee).where(Employee.id == payroll_item.employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee or employee.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    return PaymentRecordResponse.model_validate(payment)


@router.post("/{payment_id}/retry")
async def retry_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重试发薪"""
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found"
        )

    # Verify tenant
    result = await db.execute(
        select(PayrollItem).where(PayrollItem.id == payment.payroll_item_id)
    )
    payroll_item = result.scalar_one_or_none()
    if not payroll_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll item not found"
        )

    result = await db.execute(
        select(Employee).where(Employee.id == payroll_item.employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee or employee.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    if payment.status == "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already successful"
        )

    # Check if employee has wechat info
    if not employee.wechat_openid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee does not have WeChat OpenID"
        )

    # TODO: Call WeChat Pay API to retry transfer
    # For now, simulate retry
    payment.status = "pending"
    payment.error_code = None
    payment.error_message = None

    await db.commit()
    await db.refresh(payment)

    return {
        "id": payment.id,
        "status": payment.status,
        "message": "Payment retry initiated"
    }
