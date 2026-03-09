from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import auth, tenant, department, employee, salary, payroll, payment

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_db()


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tenant.router, prefix="/api/v1")
app.include_router(department.router, prefix="/api/v1")
app.include_router(employee.router, prefix="/api/v1")
app.include_router(salary.router, prefix="/api/v1")
app.include_router(payroll.router, prefix="/api/v1")
app.include_router(payment.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Salary Platform API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
