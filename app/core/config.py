import os
import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import Optional


# Get project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = BASE_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


config_data = load_config()


class Settings:
    """Application settings loaded from config.yaml"""

    def __init__(self):
        app_config = config_data.get("app", {})
        db_config = config_data.get("database", {})
        jwt_config = config_data.get("jwt", {})
        wechat_config = config_data.get("wechat", {})

        # App settings
        self.APP_NAME = app_config.get("name", "Salary Platform")
        self.DEBUG = app_config.get("debug", True)

        # Database settings
        db_host = db_config.get("host", "localhost")
        db_port = db_config.get("port", 5432)
        db_username = db_config.get("username", "postgres")
        db_password = db_config.get("password", "postgres")
        db_database = db_config.get("database", "salary")
        self.DATABASE_URL = f"postgresql+asyncpg://{db_username}:{db_password}@{db_host}:{db_port}/{db_database}"

        # JWT settings
        self.SECRET_KEY = jwt_config.get("secret_key", "your-secret-key-change-in-production")
        self.ALGORITHM = jwt_config.get("algorithm", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = jwt_config.get("access_token_expire_minutes", 1440)

        # WeChat Pay settings
        self.WECHAT_MCHID = wechat_config.get("mchid", "")
        self.WECHAT_SERIAL_NO = wechat_config.get("serial_no", "")
        self.WECHAT_PRIVATE_KEY_PATH = wechat_config.get("private_key_path", "")
        self.WECHAT_APIV3_KEY = wechat_config.get("apiv3_key", "")


settings = Settings()
