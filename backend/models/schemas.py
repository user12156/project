# 초보자 안내:
# 프론트엔드와 백엔드가 주고받는 데이터 모양을 Pydantic 모델로 정의한 파일입니다.
# MongoDB 컬렉션 구조는 지금은 프로젝트 문서 내부에 저장하고,
# 화면 안정화 후 세부 컬렉션으로 분리할 수 있게 초안 모델을 같이 둡니다.

from typing import Any

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    """회원가입 요청 body입니다."""

    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=4, max_length=128)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=20)


class KakaoAuthRequest(BaseModel):
    code: str = Field(..., min_length=4)
    redirect_uri: str | None = None


class NaverAuthRequest(BaseModel):
    code: str = Field(..., min_length=4)
    state: str = Field(..., min_length=4)
    redirect_uri: str | None = None


class LoginRequest(BaseModel):
    """로그인 요청 body입니다."""

    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=4, max_length=128)


class ProfileUpdateRequest(BaseModel):
    """프로필 닉네임 변경 요청 body입니다."""

    username: str = Field(..., min_length=3, max_length=40)


class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청 body입니다."""

    current_password: str = Field(..., min_length=4, max_length=128)
    new_password: str = Field(..., min_length=4, max_length=128)


class AuthUser(BaseModel):
    """프론트에 노출해도 되는 사용자 정보입니다. 비밀번호 해시는 절대 내려주지 않습니다."""

    id: str
    username: str


class AuthResponse(BaseModel):
    """회원가입/로그인 성공 시 내려주는 인증 응답입니다."""

    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class StoredFile(BaseModel):
    """project_files 컬렉션에 저장할 파일 메타데이터입니다."""

    id: str | None = None
    projectId: str
    name: str
    size: int | None = None
    type: str | None = None
    lastModified: int | None = None
    storagePath: str | None = None
    uploadedBy: str | None = None
    createdAt: str | None = None


class ChatMessage(BaseModel):
    """project_threads 컬렉션에 저장할 분석 대화 메시지입니다."""

    id: str
    projectId: str
    role: str
    text: str = ""
    user: str | None = None
    createdAt: str | None = None
    sourceType: str | None = None
    rows: list[dict[str, Any]] | None = None
    suggestedQuestions: list[str] | None = None


class VisualAsset(BaseModel):
    """visual_assets 컬렉션에 저장할 시각화 자료입니다."""

    id: str
    projectId: str
    projectTitle: str | None = None
    kind: str
    title: str
    desc: str | None = None
    details: list[Any] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    dataUrl: str | None = None
    saved: bool = False
    date: str | None = None
    createdAt: str | None = None


class SourceProjectRef(BaseModel):
    """공유 분석 카드가 참조한 원본 프로젝트 정보입니다."""

    id: str
    title: str
    inviteCode: str | None = None


class SharedRoomMember(BaseModel):
    """shared_rooms.members 안에 들어갈 참여자 정보입니다."""

    id: str | int
    name: str
    role: str | None = None
    joinedAt: str | None = None


class SharedRoomDraft(BaseModel):
    """shared_rooms 컬렉션에 저장할 공유방 문서입니다."""

    inviteCode: str
    joinedCode: str | None = None
    mainProjectId: str | None = None
    loadedProjectIds: list[str] = Field(default_factory=list)
    members: list[SharedRoomMember] = Field(default_factory=list)
    createdBy: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None


class DiscussionComment(BaseModel):
    """discussion_comments 컬렉션에 저장할 공유 토론 댓글입니다."""

    id: str
    roomInviteCode: str
    projectId: str | None = None
    projectTitle: str | None = None
    assetId: str | None = None
    user: str
    text: str
    time: str | None = None
    createdAt: str | None = None


class VisualAssetPayload(BaseModel):
    visual: VisualAsset


class VisualAssetResponse(BaseModel):
    visual: VisualAsset


class VisualAssetListResponse(BaseModel):
    visuals: list[VisualAsset] = Field(default_factory=list)


class SharedRoomPayload(BaseModel):
    room: SharedRoomDraft


class SharedRoomResponse(BaseModel):
    room: SharedRoomDraft


class SharedRoomListResponse(BaseModel):
    rooms: list[SharedRoomDraft] = Field(default_factory=list)


class DiscussionCommentPayload(BaseModel):
    comment: DiscussionComment


class DiscussionCommentResponse(BaseModel):
    comment: DiscussionComment


class DiscussionCommentListResponse(BaseModel):
    comments: list[DiscussionComment] = Field(default_factory=list)


class ProjectThreadPayload(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)


class ProjectThreadResponse(BaseModel):
    projectId: str
    messages: list[ChatMessage] = Field(default_factory=list)


class ProjectFilePayload(BaseModel):
    file: StoredFile


class ProjectFileResponse(BaseModel):
    file: StoredFile


class ProjectFileListResponse(BaseModel):
    files: list[StoredFile] = Field(default_factory=list)


class ProjectPayload(BaseModel):
    # 프론트 프로젝트 카드/분석/공유 데이터는 아직 형태가 자주 바뀌므로
    # MongoDB에는 JSON 객체 전체를 저장하고, 화면 안정화 후 세부 스키마를 고정합니다.
    # 필수로 기대하는 핵심 필드는 project.id, project.title, project.inviteCode 입니다.
    project: dict[str, Any]


class ProjectListPayload(BaseModel):
    """브라우저에 있는 프로젝트 배열을 백엔드와 동기화할 때 쓰는 요청 body입니다."""

    projects: list[dict[str, Any]] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    """프로젝트 하나를 저장하거나 초대코드로 조회했을 때의 응답입니다."""

    project: dict[str, Any]


class ProjectListResponse(BaseModel):
    """프로젝트 목록 조회/동기화 응답입니다."""

    projects: list[dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """서버와 MongoDB 상태 확인 응답입니다."""

    status: str
    database: str
    connected: bool
    error: str | None = None


class AnalysisDocument(BaseModel):
    """업로드 파일에서 추출한 분석용 문서 메타데이터입니다."""

    filename: str
    format: str
    chars: int = 0


class AnalysisResponse(BaseModel):
    """분석 Q&A API가 프론트에 내려주는 표준 응답입니다."""

    answer: str
    documents: list[dict[str, Any]] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    relevant_chunks: list[dict[str, Any]] = Field(default_factory=list)
    intent: str | None = None
    llm_used: bool = False
    llm_key_received: bool = False
    llm_key_source: str | None = None
    provider: str | None = None
    model: str | None = None
    llm_error: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)
    web_sources: list[dict[str, Any]] = Field(default_factory=list)


class VisualResponse(BaseModel):
    """표/그래프/이미지/마인드맵 생성 API 응답입니다."""

    visual: dict[str, Any]


class MessageResponse(BaseModel):
    """단순 성공 메시지 응답입니다."""

    message: str
