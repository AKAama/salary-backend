from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.core.database import get_db
from app.models.models import User, Employee
from app.schemas.schemas import (
    EmployeeResponse, EmployeeCreate, EmployeeUpdate,
    EmployeeListResponse
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/employees", tags=["员工"])


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: Optional[int] = None,
    status: Optional[bool] = True,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Employee).where(Employee.tenant_id == current_user.tenant_id)

    if department_id is not None:
        query = query.where(Employee.department_id == department_id)
    if status is not None:
        query = query.where(Employee.status == status)
    if keyword:
        query = query.where(
            (Employee.name.like(f"%{keyword}%")) |
            (Employee.phone.like(f"%{keyword}%")) |
            (Employee.email.like(f"%{keyword}%"))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    employees = result.scalars().all()

    return EmployeeListResponse(
        total=total,
        items=[EmployeeResponse.model_validate(e) for e in employees]
    )


@router.post("", response_model=EmployeeResponse)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if phone already exists in tenant
    result = await db.execute(
        select(Employee).where(
            Employee.tenant_id == current_user.tenant_id,
            Employee.phone == employee_data.phone
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already exists"
        )

    employee = Employee(
        tenant_id=current_user.tenant_id,
        name=employee_data.name,
        id_card=employee_data.id_card,
        phone=employee_data.phone,
        email=employee_data.email,
        department_id=employee_data.department_id,
        entry_date=employee_data.entry_date,
        position=employee_data.position,
        wechat_openid=employee_data.wechat_openid,
        wechat_real_name=employee_data.wechat_real_name,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return EmployeeResponse.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.tenant_id == current_user.tenant_id
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    return EmployeeResponse.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.tenant_id == current_user.tenant_id
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    # Check phone uniqueness if being updated
    if employee_data.phone and employee_data.phone != employee.phone:
        result = await db.execute(
            select(Employee).where(
                Employee.tenant_id == current_user.tenant_id,
                Employee.phone == employee_data.phone,
                Employee.id != employee_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists"
            )

    update_data = employee_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.commit()
    await db.refresh(employee)
    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.tenant_id == current_user.tenant_id
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    await db.delete(employee)
    await db.commit()
    return {"message": "Employee deleted successfully"}
