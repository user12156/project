# 초보자 안내:
# MongoDB 연결, 컬렉션 이름, 인덱스 생성, DB 상태 확인을 담당하는 공통 파일입니다.

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from app.core.config import settings

MONGO_DB_NAME = settings.mongo_db_name

# 컬렉션 이름을 상수로 두면 라우터와 문서에서 같은 이름을 쓰기 쉬워집니다.
USERS_COLLECTION = "users"
PROJECTS_COLLECTION = "projects"
VISUAL_ASSETS_COLLECTION = "visual_assets"
SHARED_ROOMS_COLLECTION = "shared_rooms"
DISCUSSION_COMMENTS_COLLECTION = "discussion_comments"
PROJECT_THREADS_COLLECTION = "project_threads"
PROJECT_FILES_COLLECTION = "project_files"

# serverSelectionTimeoutMS를 짧게 두면 MongoDB가 꺼져 있을 때 서버가 오래 멈추지 않습니다.
client = AsyncIOMotorClient(settings.mongo_url, serverSelectionTimeoutMS=settings.mongo_timeout_ms)
db = client[MONGO_DB_NAME]


async def ensure_indexes() -> bool:
    """자주 조회하는 필드에 인덱스를 만들어 MongoDB 검색을 빠르게 합니다."""

    try:
        # users.username: 로그인 아이디 중복 가입 방지와 로그인 조회용입니다.
        await db[USERS_COLLECTION].create_index("username", unique=True)
        await db[USERS_COLLECTION].create_index("google_sub", unique=True, sparse=True)
        await db[USERS_COLLECTION].create_index("kakao_id", unique=True, sparse=True)
        await db[USERS_COLLECTION].create_index("naver_id", unique=True, sparse=True)
        await db[USERS_COLLECTION].create_index("email", sparse=True)

        # projects는 사용자별 프로젝트 id가 중복되지 않게 저장합니다.
        await db[PROJECTS_COLLECTION].create_index([("user_id", 1), ("project.id", 1)], unique=True)

        # 초대코드 조회와 최신 프로젝트 정렬에 사용하는 인덱스입니다.
        await db[PROJECTS_COLLECTION].create_index("invite_code")
        await db[PROJECTS_COLLECTION].create_index("project.inviteCode")
        await db[PROJECTS_COLLECTION].create_index("updated_at")

        # 기능별 분리 컬렉션입니다. 프론트 전환 중에도 프로젝트 본문 저장과 병행할 수 있습니다.
        await db[VISUAL_ASSETS_COLLECTION].create_index([("user_id", 1), ("project_id", 1), ("asset.id", 1)], unique=True)
        await db[VISUAL_ASSETS_COLLECTION].create_index([("project_id", 1), ("updated_at", -1)])

        await db[SHARED_ROOMS_COLLECTION].create_index("invite_code", unique=True)
        await db[SHARED_ROOMS_COLLECTION].create_index([("created_by", 1), ("updated_at", -1)])
        await db[SHARED_ROOMS_COLLECTION].create_index("loaded_project_ids")

        await db[DISCUSSION_COMMENTS_COLLECTION].create_index([("room_invite_code", 1), ("created_at", 1)])
        await db[DISCUSSION_COMMENTS_COLLECTION].create_index([("user_id", 1), ("comment.id", 1)], unique=True)

        await db[PROJECT_THREADS_COLLECTION].create_index([("user_id", 1), ("project_id", 1)], unique=True)
        await db[PROJECT_THREADS_COLLECTION].create_index([("project_id", 1), ("updated_at", -1)])

        await db[PROJECT_FILES_COLLECTION].create_index([("user_id", 1), ("project_id", 1), ("file.id", 1)], unique=True)
        await db[PROJECT_FILES_COLLECTION].create_index([("project_id", 1), ("updated_at", -1)])
    except (PyMongoError, ServerSelectionTimeoutError):
        # MongoDB가 꺼져 있어도 문서 분석처럼 DB가 필요 없는 기능은 계속 사용할 수 있게 합니다.
        return False
    return True


async def ping_database() -> dict[str, Any]:
    """health check에서 MongoDB 연결 상태를 보여주기 위한 함수입니다."""

    try:
        await client.admin.command("ping")
    except PyMongoError as exc:
        return {"database": MONGO_DB_NAME, "connected": False, "error": str(exc)}
    return {"database": MONGO_DB_NAME, "connected": True}


def close_database() -> None:
    """서버 종료 시 MongoDB 연결을 정리합니다."""

    client.close()
