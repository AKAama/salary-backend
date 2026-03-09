from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    HR = "hr"
    EMPLOYEE = "employee"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    PROCESSING = "processing"


# === Tenant Schemas ===
class TenantBase(BaseModel):
    name: str
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    business_license: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    business_license: Optional[str] = None
    wechat_mchid: Optional[str] = None


class TenantResponse(TenantBase):
    id: int
    wechat_mchid: Optional[str] = None
    status: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === User Schemas ===
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.HR


class UserCreate(UserBase):
    password: str
    tenant_id: int


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# === Department Schemas ===
class DepartmentBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    description: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    id: int
    tenant_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# === Employee Schemas ===
class EmployeeBase(BaseModel):
    name: str
    id_card: Optional[str] = None
    phone: str
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    entry_date: Optional[date] = None
    position: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    wechat_openid: Optional[str] = None
    wechat_real_name: Optional[str] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    entry_date: Optional[date] = None
    position: Optional[str] = None
    wechat_openid: Optional[str] = None
    wechat_real_name: Optional[str] = None
    status: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    id: int
    tenant_id: int
    wechat_openid: Optional[str] = None
    wechat_real_name: Optional[str] = None
    status: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    total: int
    items: List[EmployeeResponse]


# === Salary Template Schemas ===
class SalaryItemBase(BaseModel):
    name: str
    item_type: str  # base, bonus, allowance, deduction
    is_taxable: bool = True
    is_default: bool = False
    order: int = 0


class SalaryItemCreate(SalaryItemBase):
    pass


class SalaryItemResponse(SalaryItemBase):
    id: int
    template_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SalaryTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False


class SalaryTemplateCreate(SalaryTemplateBase):
    items: Optional[List[SalaryItemCreate]] = None


class SalaryTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


class SalaryTemplateResponse(SalaryTemplateBase):
    id: int
    tenant_id: int
    created_at: datetime
    items: List[SalaryItemResponse] = []

    class Config:
        from_attributes = True


# === Salary Record Schemas ===
class SalaryRecordCreate(BaseModel):
    employee_id: int
    salary_item_id: int
    amount: Decimal = Field(..., decimal_places=2)
    effective_date: date


class SalaryRecordResponse(BaseModel):
    id: int
    employee_id: int
    salary_item_id: int
    amount: Decimal
    effective_date: date
    created_at: datetime

    class Config:
        from_attributes = True


# === Payroll Schemas ===
class PayrollItemDetailCreate(BaseModel):
    salary_item_id: int
    salary_item_name: str
    amount: Decimal
    is_taxable: bool = True


class PayrollItemCreate(BaseModel):
    employee_id: int
    gross_salary: Decimal
    net_salary: Decimal
    tax_amount: Decimal = 0
    details: List[PayrollItemDetailCreate]


class PayrollCreate(BaseModel):
    month: str  # YYYY-MM
    remark: Optional[str] = None
    items: List[PayrollItemCreate]


class PayrollItemDetailResponse(PayrollItemDetailCreate):
    id: int

    class Config:
        from_attributes = True


class PayrollItemResponse(BaseModel):
    id: int
    payroll_id: int
    employee_id: int
    gross_salary: Decimal
    net_salary: Decimal
    tax_amount: Decimal
    status: str
    details: List[PayrollItemDetailResponse] = []

    class Config:
        from_attributes = True


class PayrollResponse(BaseModel):
    id: int
    tenant_id: int
    month: str
    total_amount: Decimal
    total_count: int
    status: str
    remark: Optional[str]
    created_at: datetime
    items: List[PayrollItemResponse] = []

    class Config:
        from_attributes = True


class PayrollListResponse(BaseModel):
    total: int
    items: List[PayrollResponse]


# === Payment Schemas ===
class PaymentRecordResponse(BaseModel):
    id: int
    payroll_item_id: int
    amount: Decimal
    status: PaymentStatus
    wechat_transaction_id: Optional[str]
    wechat_batch_id: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentRetryRequest(BaseModel):
    payment_record_id: int


class PaymentListResponse(BaseModel):
    total: int
    items: List[PaymentRecordResponse]


# === WeChat Config Schemas ===
class WeChatConfigBase(BaseModel):
    mchid: str
    appid: str
    api_key: str
    serial_no: str
    private_key: str


class WeChatConfigCreate(WeChatConfigBase):
    pass


class WeChatConfigUpdate(BaseModel):
    mchid: Optional[str] = None
    appid: Optional[str] = None
    api_key: Optional[str] = None
    serial_no: Optional[str] = None
    private_key: Optional[str] = None
    status: Optional[bool] = None


class WeChatConfigResponse(WeChatConfigBase):
    id: int
    tenant_id: int
    status: bool
    created_at: datetime

    class Config:
        from_attributes = True
