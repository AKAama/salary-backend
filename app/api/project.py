from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.core.database import get_db
from app.models.models import User, Project, Employee, ProjectEmployee, ProjectEmployeeAdjustment
from app.schemas.schemas import (
    ProjectResponse, ProjectCreate, ProjectUpdate,
    ProjectListResponse, ProjectEmployeeCreate, ProjectEmployeeUpdate,
    ProjectEmployeeResponse, ProjectEmployeeListResponse,
    ProjectEmployeeAdjustmentCreate, ProjectEmployeeAdjustmentResponse,
    ProjectEmployeeWithAdjustmentsResponse
)
from app.api.deps import get_current_user
from datetime import date

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目列表"""
    query = select(Project).where(Project.tenant_id == current_user.tenant_id)

    if status:
        query = query.where(Project.status == status)
    if keyword:
        query = query.where(
            (Project.name.like(f"%{keyword}%")) |
            (Project.client_name.like(f"%{keyword}%"))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    # Get employee count for each project
    items = []
    for p in projects:
        # Count project employees
        emp_count_query = select(func.count()).select_from(ProjectEmployee).where(
            ProjectEmployee.project_id == p.id
        )
        emp_result = await db.execute(emp_count_query)
        emp_count = emp_result.scalar()

        items.append(ProjectResponse(
            id=p.id,
            tenant_id=p.tenant_id,
            name=p.name,
            client_name=p.client_name,
            description=p.description,
            start_date=p.start_date,
            end_date=p.end_date,
            status=p.status,
            remark=p.remark,
            created_by=p.created_by,
            employee_count=emp_count,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))

    return ProjectListResponse(total=total, items=items)


@router.post("", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建项目"""
    project = Project(
        tenant_id=current_user.tenant_id,
        name=project_data.name,
        client_name=project_data.client_name,
        description=project_data.description,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
        status=project_data.status,
        remark=project_data.remark,
        created_by=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        tenant_id=project.tenant_id,
        name=project.name,
        client_name=project.client_name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        status=project.status,
        remark=project.remark,
        created_by=project.created_by,
        employee_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目详情"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Count employees
    emp_count_query = select(func.count()).select_from(ProjectEmployee).where(
        ProjectEmployee.project_id == project.id
    )
    emp_result = await db.execute(emp_count_query)
    emp_count = emp_result.scalar()

    return ProjectResponse(
        id=project.id,
        tenant_id=project.tenant_id,
        name=project.name,
        client_name=project.client_name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        status=project.status,
        remark=project.remark,
        created_by=project.created_by,
        employee_count=emp_count,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新项目"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    # Get employee count
    emp_count_query = select(func.count()).select_from(ProjectEmployee).where(
        ProjectEmployee.project_id == project.id
    )
    emp_result = await db.execute(emp_count_query)
    emp_count = emp_result.scalar()

    return ProjectResponse(
        id=project.id,
        tenant_id=project.tenant_id,
        name=project.name,
        client_name=project.client_name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        status=project.status,
        remark=project.remark,
        created_by=project.created_by,
        employee_count=emp_count,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除项目"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted successfully"}


# === Project Employee (兼职员工) APIs ===

@router.get("/{project_id}/employees", response_model=ProjectEmployeeListResponse)
async def list_project_employees(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目员工列表（包括临时工）"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get project employees
    query = select(ProjectEmployee).where(
        ProjectEmployee.project_id == project_id,
        ProjectEmployee.status == True
    ).order_by(ProjectEmployee.created_at.desc())

    result = await db.execute(query)
    employees = result.scalars().all()

    items = [ProjectEmployeeResponse.model_validate(e) for e in employees]
    return ProjectEmployeeListResponse(total=len(items), items=items)


@router.post("/{project_id}/employees", response_model=ProjectEmployeeResponse)
async def add_project_employee(
    project_id: int,
    employee_data: ProjectEmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加项目员工（支持正式员工或临时工）"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # If employee_id provided, verify it's a valid employee
    if employee_data.employee_id:
        result = await db.execute(
            select(Employee).where(
                Employee.id == employee_data.employee_id,
                Employee.tenant_id == current_user.tenant_id
            )
        )
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        # Use employee info
        name = employee.name
        phone = employee.phone
        wechat_openid = employee.wechat_openid
        wechat_real_name = employee.wechat_real_name
    else:
        # Temp employee - use provided info
        if not employee_data.name or not employee_data.phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name and phone are required for temp employees"
            )
        name = employee_data.name
        phone = employee_data.phone
        wechat_openid = employee_data.wechat_openid
        wechat_real_name = employee_data.wechat_real_name

    # Check if already added (by phone if temp, by employee_id if formal)
    if employee_data.employee_id:
        result = await db.execute(
            select(ProjectEmployee).where(
                ProjectEmployee.project_id == project_id,
                ProjectEmployee.employee_id == employee_data.employee_id
            )
        )
    else:
        result = await db.execute(
            select(ProjectEmployee).where(
                ProjectEmployee.project_id == project_id,
                ProjectEmployee.phone == employee_data.phone
            )
        )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee already in project"
        )

    # Create project employee
    project_employee = ProjectEmployee(
        project_id=project_id,
        employee_id=employee_data.employee_id,
        name=name,
        phone=phone,
        id_card=employee_data.id_card,
        wechat_openid=wechat_openid,
        wechat_real_name=wechat_real_name,
        salary_type=employee_data.salary_type,
        hourly_rate=employee_data.hourly_rate,
        daily_rate=employee_data.daily_rate,
        remarks=employee_data.remarks,
    )
    db.add(project_employee)
    await db.commit()
    await db.refresh(project_employee)

    return ProjectEmployeeResponse.model_validate(project_employee)


@router.put("/{project_id}/employees/{project_employee_id}", response_model=ProjectEmployeeResponse)
async def update_project_employee(
    project_id: int,
    project_employee_id: int,
    employee_data: ProjectEmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新项目员工信息（薪资、备注等）"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get project employee
    result = await db.execute(
        select(ProjectEmployee).where(
            ProjectEmployee.id == project_employee_id,
            ProjectEmployee.project_id == project_id
        )
    )
    project_employee = result.scalar_one_or_none()
    if not project_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project employee not found"
        )

    # Update fields
    update_data = employee_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project_employee, field, value)

    await db.commit()
    await db.refresh(project_employee)

    return ProjectEmployeeResponse.model_validate(project_employee)


@router.delete("/{project_id}/employees/{project_employee_id}")
async def remove_project_employee(
    project_id: int,
    project_employee_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """移除项目员工"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get and remove project employee
    result = await db.execute(
        select(ProjectEmployee).where(
            ProjectEmployee.id == project_employee_id,
            ProjectEmployee.project_id == project_id
        )
    )
    project_employee = result.scalar_one_or_none()
    if not project_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project employee not found"
        )

    project_employee.status = False
    await db.commit()

    return {"message": "Employee removed from project successfully"}


# === Project Employee Adjustment (调薪) APIs ===

@router.get("/{project_id}/employees/{project_employee_id}/adjustments", response_model=List[ProjectEmployeeAdjustmentResponse])
async def list_adjustments(
    project_id: int,
    project_employee_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目员工的调薪记录"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get adjustments
    result = await db.execute(
        select(ProjectEmployeeAdjustment).where(
            ProjectEmployeeAdjustment.project_employee_id == project_employee_id
        ).order_by(ProjectEmployeeAdjustment.created_at.desc())
    )
    adjustments = result.scalars().all()

    return [ProjectEmployeeAdjustmentResponse.model_validate(a) for a in adjustments]


@router.post("/{project_id}/employees/{project_employee_id}/adjustments", response_model=ProjectEmployeeAdjustmentResponse)
async def add_adjustment(
    project_id: int,
    project_employee_id: int,
    adjustment_data: ProjectEmployeeAdjustmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加调薪记录（加钱/扣钱）"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Verify project employee exists
    result = await db.execute(
        select(ProjectEmployee).where(
            ProjectEmployee.id == project_employee_id,
            ProjectEmployee.project_id == project_id
        )
    )
    project_employee = result.scalar_one_or_none()
    if not project_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project employee not found"
        )

    # Create adjustment
    adjustment = ProjectEmployeeAdjustment(
        project_employee_id=project_employee_id,
        adjustment_type=adjustment_data.adjustment_type.value,
        amount=adjustment_data.amount,
        reason=adjustment_data.reason,
        created_by=current_user.id,
    )
    db.add(adjustment)
    await db.commit()
    await db.refresh(adjustment)

    return ProjectEmployeeAdjustmentResponse.model_validate(adjustment)


@router.delete("/{project_id}/employees/{project_employee_id}/adjustments/{adjustment_id}")
async def delete_adjustment(
    project_id: int,
    project_employee_id: int,
    adjustment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除调薪记录"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get and delete adjustment
    result = await db.execute(
        select(ProjectEmployeeAdjustment).where(
            ProjectEmployeeAdjustment.id == adjustment_id,
            ProjectEmployeeAdjustment.project_employee_id == project_employee_id
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adjustment not found"
        )

    await db.delete(adjustment)
    await db.commit()

    return {"message": "Adjustment deleted successfully"}


# === Quick Pay (一键发薪) ===

@router.post("/{project_id}/employees/{project_employee_id}/pay")
async def quick_pay(
    project_id: int,
    project_employee_id: int,
    work_hours: float = Query(..., ge=0),  # 工作时长（小时）
    work_days: float = Query(None, ge=0),  # 工作天数（天）
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """一键发薪给项目员工"""
    # Verify project belongs to tenant
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get project employee
    result = await db.execute(
        select(ProjectEmployee).where(
            ProjectEmployee.id == project_employee_id,
            ProjectEmployee.project_id == project_id
        )
    )
    project_employee = result.scalar_one_or_none()
    if not project_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project employee not found"
        )

    if not project_employee.wechat_openid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee has no WeChat account linked"
        )

    # Calculate amount
    total_adjustment = 0
    result = await db.execute(
        select(ProjectEmployeeAdjustment).where(
            ProjectEmployeeAdjustment.project_employee_id == project_employee_id
        )
    )
    adjustments = result.scalars().all()
    for adj in adjustments:
        if adj.adjustment_type == "bonus":
            total_adjustment += float(adj.amount)
        else:  # deduction
            total_adjustment -= float(adj.amount)

    # Calculate base salary
    if project_employee.salary_type == "daily":
        days = work_days if work_days else 0
        base_salary = float(project_employee.daily_rate) * days
    else:
        hours = work_hours if work_hours else 0
        base_salary = float(project_employee.hourly_rate) * hours

    total_amount = base_salary + total_adjustment

    if total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amount"
        )

    # TODO: Integrate with WeChat Pay API
    # For now, just return the calculated amount
    return {
        "message": "Payment initiated",
        "amount": total_amount,
        "base_salary": base_salary,
        "adjustments": total_adjustment,
        "employee_name": project_employee.name,
        "wechat_openid": project_employee.wechat_openid,
        "project_name": project.name
    }
