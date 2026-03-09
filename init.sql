-- Salary Platform Database Initialization Script
-- PostgreSQL

-- Create tables
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    contact_name VARCHAR(100),
    contact_phone VARCHAR(20),
    business_license VARCHAR(255),
    wechat_mchid VARCHAR(50),
    status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'hr',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    parent_id INTEGER REFERENCES departments(id),
    manager_id INTEGER,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    department_id INTEGER REFERENCES departments(id),
    name VARCHAR(100) NOT NULL,
    id_card VARCHAR(20),
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    wechat_openid VARCHAR(100),
    wechat_real_name VARCHAR(100),
    entry_date DATE,
    position VARCHAR(100),
    status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS salary_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS salary_items (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES salary_templates(id),
    name VARCHAR(100) NOT NULL,
    item_type VARCHAR(20),
    is_taxable BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS salary_records (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    salary_item_id INTEGER NOT NULL REFERENCES salary_items(id),
    amount DECIMAL(12, 2) DEFAULT 0,
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payrolls (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    month VARCHAR(7) NOT NULL,
    total_amount DECIMAL(12, 2) DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    remark TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payroll_items (
    id SERIAL PRIMARY KEY,
    payroll_id INTEGER NOT NULL REFERENCES payrolls(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    gross_salary DECIMAL(12, 2) DEFAULT 0,
    net_salary DECIMAL(12, 2) DEFAULT 0,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payroll_item_details (
    id SERIAL PRIMARY KEY,
    payroll_item_id INTEGER NOT NULL REFERENCES payroll_items(id),
    salary_item_id INTEGER NOT NULL,
    salary_item_name VARCHAR(100),
    amount DECIMAL(12, 2) DEFAULT 0,
    is_taxable BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS payment_records (
    id SERIAL PRIMARY KEY,
    payroll_item_id INTEGER NOT NULL REFERENCES payroll_items(id),
    amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    wechat_transaction_id VARCHAR(100),
    wechat_batch_id VARCHAR(100),
    error_code VARCHAR(50),
    error_message TEXT,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wechat_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    mchid VARCHAR(50),
    appid VARCHAR(50),
    api_key VARCHAR(100),
    serial_no VARCHAR(100),
    private_key TEXT,
    status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_employees_tenant_id ON employees(tenant_id);
CREATE INDEX IF NOT EXISTS idx_employees_department_id ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_departments_tenant_id ON departments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payrolls_tenant_id ON payrolls(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payroll_items_payroll_id ON payroll_items(payroll_id);
CREATE INDEX IF NOT EXISTS idx_payment_records_payroll_item_id ON payment_records(payroll_item_id);
