"""배포/원복 진행 중 동시 작업 방지."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.deployment.infrastructure.sqlalchemy_models import DeploymentORM


async def check_no_active_deployment(db: AsyncSession) -> None:
    """BUILDING 상태 배포가 있으면 HTTPException 발생."""
    from fastapi import HTTPException
    result = await db.execute(
        select(func.count(DeploymentORM.id)).where(DeploymentORM.status == "BUILDING")
    )
    count = result.scalar() or 0
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail="배포/원복이 진행 중입니다. 완료 후 다시 시도해주세요.",
        )
