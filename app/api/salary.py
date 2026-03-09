from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from typing import List, Optional
from app.core.database import get_db
from app.models.models import User, SalaryTemplate, SalaryItem, SalaryRecord, Employee
from app.schemas.schemas import (
    SalaryTemplateResponse, SalaryTemplateCreate, SalaryTemplateUpdate,
    SalaryRecordCreate, SalaryRecordResponse, SalaryItemResponse
)
from app.api.deps import get_current_user
from datetime import date

router = APIRouter(prefix="/salary", tags=["薪资管理"])


# === Salary Template APIs ===

@router.get("/templates", response_model=List[SalaryTemplateResponse])
async def list_salary_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取薪资模板列表"""
    result = await db.execute(
        select(SalaryTemplate).where(SalaryTemplate.tenant_id == current_user.tenant_id)
    )
    templates = result.scalars().all()
    return [SalaryTemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=SalaryTemplateResponse)
async def create_salary_template(
    template_data: SalaryTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建薪资模板"""
    # If this is the default template, unset other defaults
    if template_data.is_default:
        result = await db.execute(
            select(SalaryTemplate).where(
                SalaryTemplate.tenant_id == current_user.tenant_id,
                SalaryTemplate.is_default == True
            )
        )
        for t in result.scalars().all():
            t.is_default = False

    # Create template
    template = SalaryTemplate(
        tenant_id=current_user.tenant_id,
        name=template_data.name,
        description=template_data.description,
        is_default=template_data.is_default,
    )
    db.add(template)
    await db.flush()

    # Create salary items
    if template_data.items:
        for item_data in template_data.items:
            item = SalaryItem(
                template_id=template.id,
                name=item_data.name,
                item_type=item_data.item_type,
                is_taxable=item_data.is_taxable,
                is_default=item_data.is_default,
                order=item_data.order,
            )
            db.add(item)

    await db.commit()
    await db.refresh(template)
    return SalaryTemplateResponse.model_validate(template)


@router.get("/templates/{template_id}", response_model=SalaryTemplateResponse)
async def get_salary_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取薪资模板详情"""
    result = await db.execute(
        select(SalaryTemplate).where(
            SalaryTemplate.id == template_id,
            SalaryTemplate.tenant_id == current_user.tenant_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary template not found"
        )
    return SalaryTemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=SalaryTemplateResponse)
async def update_salary_template(
    template_id: int,
    template_data: SalaryTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新薪资模板"""
    result = await db.execute(
        select(SalaryTemplate).where(
            SalaryTemplate.id == template_id,
            SalaryTemplate.tenant_id == current_user.tenant_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary template not found"
        )

    # If setting as default, unset other defaults
    if template_data.is_default:
        result = await db.execute(
            select(SalaryTemplate).where(
                SalaryTemplate.tenant_id == current_user.tenant_id,
                SalaryTemplate.is_default == True,
                SalaryTemplate.id != template_id
            )
        )
        for t in result.scalars().all():
            t.is_default = False

    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return SalaryTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}")
async def delete_salary_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除薪资模板"""
    result = await db.execute(
        select(SalaryTemplate).where(
            SalaryTemplate.id == template_id,
            SalaryTemplate.tenant_id == current_user.tenant_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary template not found"
        )

    # Delete salary items first
    await db.execute(
        delete(SalaryItem).where(SalaryItem.template_id == template_id)
    )

    await db.delete(template)
    await db.commit()
    return {"message": "Salary template deleted successfully"}


# === Salary Item APIs ===

@router.get("/templates/{template_id}/items", response_model=List[SalaryItemResponse])
async def list_salary_items(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取薪资项目列表"""
    # Verify template belongs to tenant
    result = await db.execute(
        select(SalaryTemplate).where(
            SalaryTemplate.id == template_id,
            SalaryTemplate.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary template not found"
        )

    result = await db.execute(
        select(SalaryItem).where(SalaryItem.template_id == template_id).order_by(SalaryItem.order)
    )
    items = result.scalars().all()
    return [SalaryItemResponse.model_validate(i) for i in items]


# === Salary Record APIs ===

@router.get("/records/{employee_id}", response_model=List[SalaryRecordResponse])
async def get_employee_salary_records(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取员工薪资记录"""
    # Verify employee belongs to tenant
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    # Get latest salary for each item
    result = await db.execute(
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.salary_item_id, SalaryRecord.effective_date.desc())
    )
    records = result.scalars().all()

    # Deduplicate by salary_item_id (keep latest)
    seen_items = set()
    unique_records = []
    for record in records:
        if record.salary_item_id not in seen_items:
            seen_items.add(record.salary_item_id)
            unique_records.append(record)

    return [SalaryRecordResponse.model_validate(r) for r in unique_records]


@router.post("/records", response_model=SalaryRecordResponse)
async def create_salary_record(
    record_data: SalaryRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """设置员工薪资"""
    # Verify employee belongs to tenant
    result = await db.execute(
        select(Employee).where(
            Employee.id == record_data.employee_id,
            Employee.tenant_id == current_user.tenant_id
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    # Verify salary item exists
    result = await db.execute(
        select(SalaryItem).where(SalaryItem.id == record_data.salary_item_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary item not found"
        )

    # Create or update salary record
    # Check if there's already a record for this employee + item
    result = await db.execute(
        select(SalaryRecord).where(
            and_(
                SalaryRecord.employee_id == record_data.employee_id,
                SalaryRecord.salary_item_id == record_data.salary_item_id
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing record
        existing.amount = record_data.amount
        existing.effective_date = record_data.effective_date
        await db.commit()
        await db.refresh(existing)
        return SalaryRecordResponse.model_validate(existing)
    else:
        # Create new record
        record = SalaryRecord(
            employee_id=record_data.employee_id,
            salary_item_id=record_data.salary_item_id,
            amount=record_data.amount,
            effective_date=record_data.effective_date,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return SalaryRecordResponse.model_validate(record)


@router.delete("/records/{record_id}")
async def delete_salary_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除员工薪资记录"""
    result = await db.execute(
        select(SalaryRecord).where(SalaryRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary record not found"
        )

    # Verify employee belongs to tenant
    result = await db.execute(
        select(Employee).where(
            Employee.id == record.employee_id,
            Employee.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    await db.delete(record)
    await db.commit()
    return {"message": "Salary record deleted successfully"}
