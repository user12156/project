# 초보자 안내:
# 분석 페이지에서 만든 표/그래프/이미지 자료를 프로젝트와 분리해서 저장하는 API입니다.

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.core.database import VISUAL_ASSETS_COLLECTION, db
from app.core.deps import get_current_user_id
from models.schemas import VisualAssetListResponse, VisualAssetPayload, VisualAssetResponse


router = APIRouter(prefix="/api/visual-assets", tags=["visual-assets"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _raise_database_error(exc: PyMongoError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"시각화 자료 저장소 처리 중 오류가 발생했습니다: {exc}",
    ) from exc


@router.get("", response_model=VisualAssetListResponse)
async def list_visual_assets(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """프로젝트 시각화 보관함 자료를 최신순으로 조회합니다."""

    try:
        cursor = db[VISUAL_ASSETS_COLLECTION].find({"user_id": user_id, "project_id": project_id}).sort("updated_at", -1)
        docs = [doc async for doc in cursor]
    except PyMongoError as exc:
        _raise_database_error(exc)

    return {"visuals": [doc["asset"] for doc in docs]}


@router.post("", response_model=VisualAssetResponse, status_code=status.HTTP_201_CREATED)
async def upsert_visual_asset(
    payload: VisualAssetPayload,
    user_id: str = Depends(get_current_user_id),
):
    """시각화 자료 하나를 저장하거나 같은 id의 자료를 갱신합니다."""

    asset = payload.visual.model_dump()
    project_id = asset.get("projectId")
    asset_id = asset.get("id")
    if not project_id or not asset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="visual.projectId와 visual.id가 필요합니다.")

    now = datetime.now(timezone.utc)
    asset.setdefault("createdAt", _now_iso())
    try:
        await db[VISUAL_ASSETS_COLLECTION].update_one(
            {"user_id": user_id, "project_id": project_id, "asset.id": asset_id},
            {
                "$set": {
                    "user_id": user_id,
                    "project_id": project_id,
                    "asset": asset,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    except PyMongoError as exc:
        _raise_database_error(exc)

    return {"visual": asset}


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visual_asset(
    asset_id: str,
    project_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """프로젝트 시각화 보관함에서 자료 하나를 삭제합니다."""

    try:
        result = await db[VISUAL_ASSETS_COLLECTION].delete_one(
            {"user_id": user_id, "project_id": project_id, "asset.id": asset_id}
        )
    except PyMongoError as exc:
        _raise_database_error(exc)

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="삭제할 시각화 자료를 찾지 못했습니다.")
