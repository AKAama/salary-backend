from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Salary Platform"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/salary"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # WeChat Pay
    WECHAT_MCHID: str = ""  # 商户号
    WECHAT_SERIAL_NO: str = ""  # 证书序列号
    WECHAT_PRIVATE_KEY_PATH: str = ""  # 私钥路径
    WECHAT_APIV3_KEY: str = ""  # APIv3密钥

    class Config:
        env_file = ".env"


settings = Settings()
