from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.shared.infrastructure.database import init_db
from app.shared.infrastructure.event_bus import InMemoryEventBus
from app.shared.domain.exceptions import DomainException
from app.shared.interfaces.error_handlers import domain_exception_handler

from app.audit.application.event_handlers import AuditEventHandler
from app.deployment.domain.events import DeploymentSucceeded, DeploymentFailed
from app.rollback.domain.events import RollbackExecuted

from app.git.interface.router import router as git_router
from app.deployment.interface.router import router as deploy_router
from app.analysis.interface.router import router as analysis_router
from app.rollback.interface.router import router as rollback_router
from app.sandbox.interface.router import router as sandbox_router
from app.audit.interface.router import router as audit_router
from app.review.interface.router import router as review_router

from app.deployment.interface import router as deploy_module
from app.rollback.interface import router as rollback_module
from app.shared.infrastructure.database import SessionFactory


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Wire domain event bus
    event_bus = InMemoryEventBus()
    audit_handler = AuditEventHandler(SessionFactory)

    event_bus.subscribe(DeploymentSucceeded, audit_handler.handle_deployment_succeeded)
    event_bus.subscribe(DeploymentFailed, audit_handler.handle_deployment_failed)
    event_bus.subscribe(RollbackExecuted, audit_handler.handle_rollback_executed)

    # Inject event bus into routers that need it
    deploy_module.set_event_bus(event_bus)
    rollback_module.set_event_bus(event_bus)

    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(DomainException, domain_exception_handler)

app.include_router(git_router)
app.include_router(deploy_router)
app.include_router(analysis_router)
app.include_router(rollback_router)
app.include_router(sandbox_router)
app.include_router(audit_router)
app.include_router(review_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
