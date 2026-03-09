from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import User, WeChatConfig
from app.schemas.schemas import (
    WeChatConfigResponse, WeChatConfigCreate, WeChatConfigUpdate
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/wechat", tags=["微信配置"])


@router.get("/config", response_model=WeChatConfigResponse)
async def get_wechat_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取微信配置"""
    result = await db.execute(
        select(WeChatConfig).where(
            WeChatConfig.tenant_id == current_user.tenant_id,
            WeChatConfig.status == True
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WeChat config not found"
        )
    return WeChatConfigResponse.model_validate(config)


@router.post("/config", response_model=WeChatConfigResponse)
async def create_wechat_config(
    config_data: WeChatConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建微信配置"""
    # Check if config already exists
    result = await db.execute(
        select(WeChatConfig).where(
            WeChatConfig.tenant_id == current_user.tenant_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Update existing
        for field, value in config_data.model_dump().items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return WeChatConfigResponse.model_validate(existing)

    # Create new config
    config = WeChatConfig(
        tenant_id=current_user.tenant_id,
        mchid=config_data.mchid,
        appid=config_data.appid,
        api_key=config_data.api_key,
        serial_no=config_data.serial_no,
        private_key=config_data.private_key,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return WeChatConfigResponse.model_validate(config)


@router.put("/config/{config_id}", response_model=WeChatConfigResponse)
async def update_wechat_config(
    config_id: int,
    config_data: WeChatConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新微信配置"""
    result = await db.execute(
        select(WeChatConfig).where(
            WeChatConfig.id == config_id,
            WeChatConfig.tenant_id == current_user.tenant_id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WeChat config not found"
        )

    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return WeChatConfigResponse.model_validate(config)


@router.delete("/config/{config_id}")
async def delete_wechat_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除微信配置"""
    result = await db.execute(
        select(WeChatConfig).where(
            WeChatConfig.id == config_id,
            WeChatConfig.tenant_id == current_user.tenant_id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WeChat config not found"
        )

    config.status = False
    await db.commit()
    return {"message": "WeChat config deleted successfully"}
