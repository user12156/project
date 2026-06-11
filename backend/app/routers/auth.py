# 초보자 안내: 회원가입, 로그인, 프로필 수정, 비밀번호 변경 같은 인증 API를 모아둔 파일입니다.

from datetime import datetime, timezone
import json
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request as UrlRequest, urlopen

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.config import settings
from app.core.database import (
    DISCUSSION_COMMENTS_COLLECTION,
    PROJECT_FILES_COLLECTION,
    PROJECT_THREADS_COLLECTION,
    PROJECTS_COLLECTION,
    SHARED_ROOMS_COLLECTION,
    VISUAL_ASSETS_COLLECTION,
    db,
)
from app.core.deps import get_current_user_id
from app.core.security import create_access_token, hash_password, verify_password
from models.schemas import (
    AuthResponse,
    AuthUser,
    GoogleAuthRequest,
    KakaoAuthRequest,
    LoginRequest,
    NaverAuthRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    SignupRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _raise_database_error(exc: PyMongoError) -> None:
    """MongoDB 장애를 로그인 화면에서 이해할 수 있는 오류로 바꿉니다."""

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"데이터베이스 연결 또는 처리 중 오류가 발생했습니다: {exc}",
    ) from exc


def serialize_user(user) -> AuthUser:
    return AuthUser(id=str(user["_id"]), username=user.get("display_name") or user["username"])


@router.get("/google/config")
async def google_config() -> dict[str, str]:
    return {"client_id": settings.google_client_id}


@router.get("/kakao/config")
async def kakao_config() -> dict[str, str]:
    return {
        "rest_api_key": settings.kakao_rest_api_key,
        "redirect_uri": settings.kakao_redirect_uri,
    }


@router.get("/naver/config")
async def naver_config() -> dict[str, str]:
    return {
        "client_id": settings.naver_client_id,
        "redirect_uri": settings.naver_redirect_uri,
    }


def _verify_google_id_token(id_token: str) -> dict:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 .env에 GOOGLE_CLIENT_ID 또는 VITE_GOOGLE_CLIENT_ID가 필요합니다.",
        )

    url = "https://oauth2.googleapis.com/tokeninfo?" + urlencode({"id_token": id_token})
    try:
        with urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 로그인 토큰을 검증하지 못했습니다.") from exc

    if payload.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google Client ID가 일치하지 않습니다.")
    if payload.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 토큰 발급자가 올바르지 않습니다.")
    if payload.get("email_verified") not in {"true", True}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 이메일 인증이 완료되지 않은 계정입니다.")
    if not payload.get("sub") or not payload.get("email"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 계정 정보를 읽지 못했습니다.")
    return payload


async def _unique_google_username(email: str, fallback_name: str) -> str:
    base = (email or fallback_name or "google-user").strip().lower()[:40] or "google-user"
    candidate = base
    suffix = 2
    while await db.users.find_one({"username": candidate}):
        trimmed = base[: max(1, 40 - len(str(suffix)) - 1)]
        candidate = f"{trimmed}-{suffix}"
        suffix += 1
    return candidate


async def _unique_social_username(provider: str, email: str | None, fallback_name: str | None, provider_id: str) -> str:
    source = email or fallback_name or f"{provider}-{provider_id}"
    base = source.strip().lower().replace(" ", "-")[:40] or f"{provider}-user"
    candidate = base
    suffix = 2
    while await db.users.find_one({"username": candidate}):
        trimmed = base[: max(1, 40 - len(str(suffix)) - 1)]
        candidate = f"{trimmed}-{suffix}"
        suffix += 1
    return candidate


def _request_json(url: str, *, data: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> dict:
    encoded_data = None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "PaperMate/1.0",
        **(headers or {}),
    }
    if data is not None:
        encoded_data = urlencode(data).encode("utf-8")
        request_headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            **request_headers,
        }

    request = UrlRequest(url, data=encoded_data, headers=request_headers)
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _oauth_error_message(provider: str, exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        payload = {}

    description = (
        payload.get("error_description")
        or payload.get("error")
        or payload.get("msg")
        or payload.get("message")
        or str(exc)
    )
    if provider == "카카오" and "bad client credentials" in str(description).lower():
        return (
            "카카오 로그인 오류: Bad client credentials. "
            "KAKAO_REST_API_KEY에는 카카오 Developers > 앱 설정 > 앱 키의 REST API 키를 넣어야 합니다. "
            "JavaScript 키, Native 앱 키, Admin 키를 넣으면 이 오류가 납니다."
        )
    return f"{provider} 로그인 오류: {description}"


def _exchange_kakao_code(code: str, redirect_uri: str | None = None) -> dict:
    if not settings.kakao_rest_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 .env에 KAKAO_REST_API_KEY가 필요합니다.",
        )

    token_payload = {
        "grant_type": "authorization_code",
        "client_id": settings.kakao_rest_api_key,
        "redirect_uri": redirect_uri or settings.kakao_redirect_uri,
        "code": code,
    }
    if settings.kakao_client_secret:
        token_payload["client_secret"] = settings.kakao_client_secret

    try:
        token_data = _request_json("https://kauth.kakao.com/oauth/token", data=token_payload)
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Kakao access token missing")
        return _request_json(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except HTTPException:
        raise
    except HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_oauth_error_message("카카오", exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"카카오 로그인 인증에 실패했습니다: {exc}") from exc


async def _login_with_kakao_profile(kakao_user: dict) -> AuthResponse:
    kakao_id = str(kakao_user.get("id") or "").strip()
    kakao_account = kakao_user.get("kakao_account") or {}
    profile = kakao_account.get("profile") or {}
    email = (kakao_account.get("email") or "").strip().lower()
    display_name = (profile.get("nickname") or email.split("@")[0] or f"kakao-{kakao_id}").strip()
    now = datetime.now(timezone.utc)

    if not kakao_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="카카오 계정 정보를 읽지 못했습니다.")

    try:
        user = await db.users.find_one({"kakao_id": kakao_id})
        if not user and email:
            user = await db.users.find_one({"email": email})

        if user:
            update_fields = {
                "kakao_id": kakao_id,
                "display_name": user.get("display_name") or display_name,
                "auth_provider": "kakao",
                "last_login_at": now,
            }
            if email:
                update_fields["email"] = email
            await db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
            user.update(update_fields)
        else:
            username = await _unique_social_username("kakao", email or None, display_name, kakao_id)
            user = {
                "username": username,
                "display_name": display_name,
                "kakao_id": kakao_id,
                "auth_provider": "kakao",
                "created_at": now,
                "last_login_at": now,
            }
            if email:
                user["email"] = email
            result = await db.users.insert_one(user)
            user["_id"] = result.inserted_id
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 연결된 카카오 계정입니다.") from exc
    except PyMongoError as exc:
        _raise_database_error(exc)

    token = create_access_token(str(user["_id"]))
    return AuthResponse(access_token=token, user=serialize_user(user))


def _exchange_naver_code(code: str, state: str, redirect_uri: str | None = None) -> dict:
    if not settings.naver_client_id or not settings.naver_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 .env에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET이 필요합니다.",
        )

    token_payload = {
        "grant_type": "authorization_code",
        "client_id": settings.naver_client_id,
        "client_secret": settings.naver_client_secret,
        "code": code,
        "state": state,
    }
    if redirect_uri:
        token_payload["redirect_uri"] = redirect_uri

    try:
        token_data = _request_json("https://nid.naver.com/oauth2.0/token?" + urlencode(token_payload))
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Naver access token missing")
        profile_data = _request_json(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except HTTPException:
        raise
    except HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_oauth_error_message("네이버", exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"네이버 로그인 인증에 실패했습니다: {exc}") from exc

    if profile_data.get("resultcode") not in {"00", 0}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="네이버 계정 정보를 읽지 못했습니다.")
    return profile_data.get("response") or {}


async def _login_with_naver_profile(naver_profile: dict) -> AuthResponse:
    naver_id = str(naver_profile.get("id") or "").strip()
    email = (naver_profile.get("email") or "").strip().lower()
    display_name = (
        naver_profile.get("nickname")
        or naver_profile.get("name")
        or email.split("@")[0]
        or f"naver-{naver_id}"
    ).strip()
    now = datetime.now(timezone.utc)

    if not naver_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="네이버 계정 정보를 읽지 못했습니다.")

    try:
        user = await db.users.find_one({"naver_id": naver_id})
        if not user and email:
            user = await db.users.find_one({"email": email})

        if user:
            update_fields = {
                "naver_id": naver_id,
                "display_name": user.get("display_name") or display_name,
                "auth_provider": "naver",
                "last_login_at": now,
            }
            if email:
                update_fields["email"] = email
            await db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
            user.update(update_fields)
        else:
            username = await _unique_social_username("naver", email or None, display_name, naver_id)
            user = {
                "username": username,
                "display_name": display_name,
                "naver_id": naver_id,
                "auth_provider": "naver",
                "created_at": now,
                "last_login_at": now,
            }
            if email:
                user["email"] = email
            result = await db.users.insert_one(user)
            user["_id"] = result.inserted_id
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 연결된 네이버 계정입니다.") from exc
    except PyMongoError as exc:
        _raise_database_error(exc)

    token = create_access_token(str(user["_id"]))
    return AuthResponse(access_token=token, user=serialize_user(user))


def get_object_id(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 사용자입니다.") from exc


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="아이디를 입력해주세요.")

    user_doc = {
        "username": username,
        "display_name": username,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = await db.users.insert_one(user_doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 아이디입니다.") from exc
    except PyMongoError as exc:
        _raise_database_error(exc)

    user_doc["_id"] = result.inserted_id
    token = create_access_token(str(result.inserted_id))
    return AuthResponse(access_token=token, user=serialize_user(user_doc))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    username = payload.username.strip()
    try:
        user = await db.users.find_one({"username": username})
    except PyMongoError as exc:
        _raise_database_error(exc)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="등록되지 않은 아이디입니다.")

    if not user.get("password_hash"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google로 가입한 계정입니다. Google 로그인을 사용해주세요.")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="비밀번호가 올바르지 않습니다.")

    token = create_access_token(str(user["_id"]))
    return AuthResponse(access_token=token, user=serialize_user(user))


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleAuthRequest):
    google_user = _verify_google_id_token(payload.id_token)
    google_sub = google_user["sub"]
    email = google_user["email"].strip().lower()
    display_name = (google_user.get("name") or email.split("@")[0] or email).strip()
    now = datetime.now(timezone.utc)

    try:
        user = await db.users.find_one({"google_sub": google_sub})
        if not user:
            user = await db.users.find_one({"email": email})

        if user:
            await db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "google_sub": google_sub,
                        "email": email,
                        "display_name": user.get("display_name") or display_name,
                        "auth_provider": "google",
                        "last_login_at": now,
                    }
                },
            )
            user.update({
                "google_sub": google_sub,
                "email": email,
                "display_name": user.get("display_name") or display_name,
            })
        else:
            username = await _unique_google_username(email, display_name)
            user = {
                "username": username,
                "display_name": display_name,
                "email": email,
                "google_sub": google_sub,
                "auth_provider": "google",
                "created_at": now,
                "last_login_at": now,
            }
            result = await db.users.insert_one(user)
            user["_id"] = result.inserted_id
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 연결된 Google 계정입니다.") from exc
    except PyMongoError as exc:
        _raise_database_error(exc)

    token = create_access_token(str(user["_id"]))
    return AuthResponse(access_token=token, user=serialize_user(user))


@router.post("/kakao", response_model=AuthResponse)
async def kakao_login(payload: KakaoAuthRequest):
    kakao_user = _exchange_kakao_code(payload.code, payload.redirect_uri)
    return await _login_with_kakao_profile(kakao_user)


@router.post("/naver", response_model=AuthResponse)
async def naver_login(payload: NaverAuthRequest):
    naver_profile = _exchange_naver_code(payload.code, payload.state, payload.redirect_uri)
    return await _login_with_naver_profile(naver_profile)


async def kakao_oauth_callback(code: str | None = None, error: str | None = None, error_description: str | None = None):
    redirect_params: dict[str, str] = {"auth_provider": "kakao"}

    if error:
        redirect_params["auth_error"] = error_description or error
    elif not code:
        redirect_params["auth_error"] = "카카오 로그인 코드가 없습니다."
    else:
        try:
            auth_response = await kakao_login(KakaoAuthRequest(code=code, redirect_uri=settings.kakao_redirect_uri))
            redirect_params.update(
                {
                    "auth_token": auth_response.access_token,
                    "auth_user_id": auth_response.user.id,
                    "auth_username": auth_response.user.username,
                }
            )
        except HTTPException as exc:
            redirect_params["auth_error"] = str(exc.detail)

    redirect_url = settings.kakao_frontend_redirect_uri
    separator = "&" if "?" in redirect_url else "?"
    return RedirectResponse(f"{redirect_url}{separator}{urlencode(redirect_params)}")


@router.get("/kakao/callback", include_in_schema=False)
async def kakao_callback(code: str | None = None, error: str | None = None, error_description: str | None = None):
    return await kakao_oauth_callback(code=code, error=error, error_description=error_description)


async def naver_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    redirect_params: dict[str, str] = {"auth_provider": "naver"}

    if error:
        redirect_params["auth_error"] = error_description or error
    elif not code or not state:
        redirect_params["auth_error"] = "네이버 로그인 코드가 없습니다."
    else:
        try:
            auth_response = await naver_login(
                NaverAuthRequest(code=code, state=state, redirect_uri=settings.naver_redirect_uri)
            )
            redirect_params.update(
                {
                    "auth_token": auth_response.access_token,
                    "auth_user_id": auth_response.user.id,
                    "auth_username": auth_response.user.username,
                }
            )
        except HTTPException as exc:
            redirect_params["auth_error"] = str(exc.detail)

    redirect_url = settings.naver_frontend_redirect_uri
    separator = "&" if "?" in redirect_url else "?"
    return RedirectResponse(f"{redirect_url}{separator}{urlencode(redirect_params)}")


@router.get("/naver/callback", include_in_schema=False)
async def naver_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    return await naver_oauth_callback(code=code, state=state, error=error, error_description=error_description)


@router.patch("/profile", response_model=AuthUser)
async def update_profile(
    payload: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="닉네임을 입력해주세요.")

    object_id = get_object_id(user_id)
    try:
        user = await db.users.find_one({"_id": object_id})
    except PyMongoError as exc:
        _raise_database_error(exc)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    display_name = username
    try:
        await db.users.update_one({"_id": object_id}, {"$set": {"display_name": display_name}})
    except PyMongoError as exc:
        _raise_database_error(exc)

    user["display_name"] = display_name

    return serialize_user(user)


@router.patch("/password")
async def change_password(
    payload: PasswordChangeRequest,
    user_id: str = Depends(get_current_user_id),
):
    object_id = get_object_id(user_id)
    try:
        user = await db.users.find_one({"_id": object_id})
    except PyMongoError as exc:
        _raise_database_error(exc)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    if not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호가 올바르지 않습니다.")

    try:
        await db.users.update_one(
            {"_id": object_id},
            {"$set": {"password_hash": hash_password(payload.new_password)}},
        )
    except PyMongoError as exc:
        _raise_database_error(exc)

    return {"message": "비밀번호가 변경되었습니다."}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(user_id: str = Depends(get_current_user_id)):
    object_id = get_object_id(user_id)
    try:
        result = await db.users.delete_one({"_id": object_id})
    except PyMongoError as exc:
        _raise_database_error(exc)

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    try:
        await db[PROJECTS_COLLECTION].delete_many({"user_id": user_id})
        await db[VISUAL_ASSETS_COLLECTION].delete_many({"user_id": user_id})
        await db[DISCUSSION_COMMENTS_COLLECTION].delete_many({"user_id": user_id})
        await db[PROJECT_THREADS_COLLECTION].delete_many({"user_id": user_id})
        await db[PROJECT_FILES_COLLECTION].delete_many({"user_id": user_id})
        await db[SHARED_ROOMS_COLLECTION].delete_many({"created_by": user_id})
    except PyMongoError as exc:
        _raise_database_error(exc)
