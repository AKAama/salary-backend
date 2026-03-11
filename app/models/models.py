from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text, Date, Enum as SQLEnum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"      # 企业管理员
    HR = "hr"            # HR
    EMPLOYEE = "employee"  # 员工


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    PROCESSING = "processing"


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"          # 草稿
    RUNNING = "running"      # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消



class ProjectEmployee(Base):
    """项目员工（包括临时工/兼职）"""
    __tablename__ = "project_employees_new"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"))  # 关联正式员工，可选

    # 临时员工信息（不通过员工系统，直接加项目）
    name = Column(String(100), nullable=False)  # 姓名
    phone = Column(String(20), nullable=False)  # 手机号
    id_card = Column(String(20))  # 身份证
    wechat_openid = Column(String(100))  # 微信openid
    wechat_real_name = Column(String(100))  # 微信实名

    # 薪资方式：hourly=时薪，daily=日薪
    salary_type = Column(String(20), default="hourly")  # hourly / daily
    hourly_rate = Column(Numeric(10, 2), default=0)  # 时薪
    daily_rate = Column(Numeric(10, 2), default=0)  # 日薪

    remarks = Column(Text)  # 备注
    status = Column(Boolean, default=True)  # 状态

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project")
    employee = relationship("Employee")
    adjustments = relationship("ProjectEmployeeAdjustment", back_populates="project_employee")


class ProjectEmployeeAdjustment(Base):
    """项目员工调薪记录（加钱/扣钱）"""
    __tablename__ = "project_employee_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    project_employee_id = Column(Integer, ForeignKey("project_employees_new.id"), nullable=False)
    adjustment_type = Column(String(20), nullable=False)  # bonus(加钱) / deduction(扣钱)
    amount = Column(Numeric(10, 2), nullable=False)  # 金额
    reason = Column(String(255))  # 原因/备注
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    project_employee = relationship("ProjectEmployee", back_populates="adjustments")
    creator = relationship("User")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # 企业名称
    industry = Column(String(100))  # 行业
    contact_name = Column(String(100))  # 联系人
    contact_phone = Column(String(20))  # 联系电话
    business_license = Column(String(255))  # 营业执照
    wechat_mchid = Column(String(50))  # 微信商户号
    status = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="tenant")
    departments = relationship("Department", back_populates="tenant")
    employees = relationship("Employee", back_populates="tenant")
    salary_templates = relationship("SalaryTemplate", back_populates="tenant")
    payrolls = relationship("Payroll", back_populates="tenant")
    wechat_config = relationship("WeChatConfig", back_populates="tenant", uselist=False)
    projects = relationship("Project", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20))
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.HR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="users")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("departments.id"))  # 上级部门
    manager_id = Column(Integer, ForeignKey("employees.id"))  # 部门负责人
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="departments")
    parent = relationship("Department", remote_side=[id], backref="children")
    manager = relationship("Employee", foreign_keys=[manager_id])
    employees = relationship("Employee", foreign_keys="Employee.department_id", back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    name = Column(String(100), nullable=False)
    id_card = Column(String(20))  # 身份证号
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    wechat_openid = Column(String(100))  # 微信openid
    wechat_real_name = Column(String(100))  # 微信实名
    entry_date = Column(Date)  # 入职日期
    position = Column(String(100))  # 职位
    status = Column(Boolean, default=True)  # 在职状态
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="employees")
    department = relationship("Department", foreign_keys="Employee.department_id", back_populates="employees")
    salary_records = relationship("SalaryRecord", back_populates="employee")
    payroll_items = relationship("PayrollItem", back_populates="employee")
    # Removed old association - use ProjectEmployee instead


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)  # 项目名称，如"顺丰速运"
    client_name = Column(String(255))  # 客户名称
    description = Column(Text)  # 项目描述
    start_date = Column(Date)  # 开始日期
    end_date = Column(Date)  # 结束日期
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.DRAFT)  # 项目状态
    remark = Column(Text)  # 备注
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    creator = relationship("User")
    project_employees = relationship("ProjectEmployee", back_populates="project", cascade="all, delete-orphan")


class SalaryTemplate(Base):
    __tablename__ = "salary_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)  # 模板名称
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="salary_templates")
    items = relationship("SalaryItem", back_populates="template")


class SalaryItem(Base):
    __tablename__ = "salary_items"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("salary_templates.id"), nullable=False)
    name = Column(String(100), nullable=False)  # 项目名称
    item_type = Column(String(20))  # 薪资类型: base(基本工资), bonus(奖金), allowance(补贴), deduction(扣款)
    is_taxable = Column(Boolean, default=True)  # 是否计税
    is_default = Column(Boolean, default=False)  # 是否为默认项目
    order = Column(Integer, default=0)  # 排序
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    template = relationship("SalaryTemplate", back_populates="items")
    salary_records = relationship("SalaryRecord", back_populates="salary_item")


class SalaryRecord(Base):
    __tablename__ = "salary_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    salary_item_id = Column(Integer, ForeignKey("salary_items.id"), nullable=False)
    amount = Column(Numeric(12, 2), default=0)  # 金额
    effective_date = Column(Date)  # 生效日期
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    employee = relationship("Employee", back_populates="salary_records")
    salary_item = relationship("SalaryItem", back_populates="salary_records")


class Payroll(Base):
    __tablename__ = "payrolls"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))  # 关联项目
    month = Column(String(7), nullable=False)  # 工资月份: 2024-01
    total_amount = Column(Numeric(12, 2), default=0)  # 总金额
    total_count = Column(Integer, default=0)  # 人数
    status = Column(String(20), default="draft")  # draft, generated, paid
    remark = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="payrolls")
    project = relationship("Project")
    items = relationship("PayrollItem", back_populates="payroll")
    creator = relationship("User")


class PayrollItem(Base):
    __tablename__ = "payroll_items"

    id = Column(Integer, primary_key=True, index=True)
    payroll_id = Column(Integer, ForeignKey("payrolls.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    gross_salary = Column(Numeric(12, 2), default=0)  # 应发工资
    net_salary = Column(Numeric(12, 2), default=0)  # 实发工资
    tax_amount = Column(Numeric(12, 2), default=0)  # 个税
    status = Column(String(20), default="pending")  # pending, paid, failed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    payroll = relationship("Payroll", back_populates="items")
    employee = relationship("Employee", back_populates="payroll_items")
    details = relationship("PayrollItemDetail", back_populates="payroll_item")
    payment_record = relationship("PaymentRecord", back_populates="payroll_item", uselist=False)


class PayrollItemDetail(Base):
    __tablename__ = "payroll_item_details"

    id = Column(Integer, primary_key=True, index=True)
    payroll_item_id = Column(Integer, ForeignKey("payroll_items.id"), nullable=False)
    salary_item_id = Column(Integer, nullable=False)
    salary_item_name = Column(String(100))
    amount = Column(Numeric(12, 2), default=0)
    is_taxable = Column(Boolean, default=True)

    # Relationships
    payroll_item = relationship("PayrollItem", back_populates="details")


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    payroll_item_id = Column(Integer, ForeignKey("payroll_items.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    wechat_transaction_id = Column(String(100))  # 微信支付单号
    wechat_batch_id = Column(String(100))  # 微信批次单号
    error_code = Column(String(50))
    error_message = Column(Text)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    payroll_item = relationship("PayrollItem", back_populates="payment_record")


class WeChatConfig(Base):
    __tablename__ = "wechat_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    mchid = Column(String(50))  # 商户号
    appid = Column(String(50))  # 应用ID
    api_key = Column(String(100))  # API密钥
    serial_no = Column(String(100))  # 证书序列号
    private_key = Column(Text)  # 商户私钥
    status = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="wechat_config")
