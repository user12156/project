# 초보자 안내:
# 이 파일은 FastAPI 백엔드의 진입점입니다.
# 프론트엔드의 main.tsx가 React 앱을 시작하듯이, 여기서는 API 서버를 만들고
# 로그인/분석/프로젝트/시각화 라우터와 배포용 프론트 파일을 연결합니다.

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import close_database, ensure_indexes, ping_database
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router
from app.routers.document_previews import router as document_previews_router
from app.routers.discussion_comments import router as discussion_comments_router
from app.routers.project_files import router as project_files_router
from app.routers.project_threads import router as project_threads_router
from app.routers.projects import router as projects_router
from app.routers.shared_rooms import router as shared_rooms_router
from app.routers.visual_assets import router as visual_assets_router
from app.routers.visuals import router as visuals_router

RESERVED_FRONTEND_PATHS = {"docs", "openapi.json", "redoc"}

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("papermate.api")


def _frontend_build_dir() -> Path:
    """배포 빌드 결과물(dist)의 위치를 반환합니다."""

    return settings.frontend_build_dir


def _register_routers(api: FastAPI) -> None:
    """기능별 API 라우터를 FastAPI 앱에 연결합니다."""

    api.include_router(auth_router)
    api.include_router(analysis_router)
    api.include_router(document_previews_router)
    api.include_router(projects_router)
    api.include_router(visuals_router)
    api.include_router(visual_assets_router)
    api.include_router(shared_rooms_router)
    api.include_router(discussion_comments_router)
    api.include_router(project_threads_router)
    api.include_router(project_files_router)


def _mount_frontend(api: FastAPI, build_dir: Path) -> None:
    """프론트엔드 빌드 파일이 있으면 FastAPI가 함께 서빙하도록 연결합니다."""

    if not build_dir.exists():
        return

    assets_dir = build_dir / "assets"
    if assets_dir.exists():
        api.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @api.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def serve_react_app(full_path: str):
        # React Router 주소로 새로고침해도 index.html을 돌려줘야 SPA가 살아납니다.
        if full_path in RESERVED_FRONTEND_PATHS:
            return {"message": "API documentation is disabled."}

        requested_file = build_dir / full_path
        if full_path and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(build_dir / "index.html")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)


# CORS는 프론트엔드 주소에서 백엔드 API를 호출할 수 있게 허용하는 설정입니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_register_routers(app)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """요청마다 추적 ID와 처리 시간을 응답 헤더에 남깁니다."""

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error", extra={"request_id": request_id, "path": request.url.path})
        raise

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    # 추가 디버깅: 인증 실패를 조사할 때 어떤 요청이 401을 반환했는지 확인하기 쉽도록 로그를 남깁니다.
    if getattr(response, "status_code", None) == status.HTTP_401_UNAUTHORIZED:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        logger.warning(
            "Unauthorized response returned",
            extra={"request_id": request_id, "path": request.url.path, "auth_header_present": bool(auth_header)},
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-MS"] = f"{elapsed_ms:.2f}"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic 검증 오류를 프론트에서 읽기 쉬운 형태로 통일합니다."""

    logger.info("Request validation failed", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "요청 값 형식이 올바르지 않습니다.", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """예상하지 못한 예외가 내부 경로/스택을 그대로 노출하지 않도록 막습니다."""

    logger.exception("Unhandled server error", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
    )


@app.on_event("startup")
async def on_startup() -> None:
    # 서버가 켜질 때 MongoDB 검색 속도를 위한 인덱스를 준비합니다.
    # MongoDB가 꺼져 있어도 문서 분석 기능은 쓸 수 있도록 database.py에서 예외를 처리합니다.
    index_ready = await ensure_indexes()
    if not index_ready:
        logger.warning("MongoDB index setup skipped. Database may be unavailable.")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    close_database()


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    """서버 프로세스가 살아 있는지 확인하는 liveness API입니다."""

    db_status = await ping_database()
    return {"status": "ok", "environment": settings.app_env, **db_status}


@app.get("/api/ready")
async def readiness_check() -> dict[str, Any]:
    """배포 환경에서 트래픽을 받아도 되는지 확인하는 readiness API입니다."""

    db_status = await ping_database()
    if not db_status.get("connected"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=db_status)
    return {"status": "ready", "environment": settings.app_env, **db_status}


_mount_frontend(app, _frontend_build_dir())
