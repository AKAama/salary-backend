from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.models import User, Department
from app.schemas.schemas import (
    DepartmentResponse, DepartmentCreate, DepartmentUpdate
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/departments", tags=["部门"])


@router.get("", response_model=List[DepartmentResponse])
async def list_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Department).where(Department.tenant_id == current_user.tenant_id)
    )
    departments = result.scalars().all()
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.post("", response_model=DepartmentResponse)
async def create_department(
    department_data: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    department = Department(
        tenant_id=current_user.tenant_id,
        name=department_data.name,
        parent_id=department_data.parent_id,
        manager_id=department_data.manager_id,
        description=department_data.description,
    )
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return DepartmentResponse.model_validate(department)


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Department).where(
            Department.id == department_id,
            Department.tenant_id == current_user.tenant_id
        )
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return DepartmentResponse.model_validate(department)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Department).where(
            Department.id == department_id,
            Department.tenant_id == current_user.tenant_id
        )
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    update_data = department_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)

    await db.commit()
    await db.refresh(department)
    return DepartmentResponse.model_validate(department)


@router.delete("/{department_id}")
async def delete_department(
    department_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Department).where(
            Department.id == department_id,
            Department.tenant_id == current_user.tenant_id
        )
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    await db.delete(department)
    await db.commit()
    return {"message": "Department deleted successfully"}
