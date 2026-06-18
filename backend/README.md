PaperMate
=========

PaperMate는 PDF, HWPX, DOCX, 이미지, TXT 문서를 업로드해 분석하고, 결과를 프로젝트로 저장해 협업할 수 있는 문서 분석 웹 애플리케이션입니다.

주요 기능
---------

- 문서 업로드 및 분석
- AI 기반 질의응답
- 문서 원본 미리보기와 분석 결과 비교
- 표, 그래프 등 시각화 자료 생성
- 프로젝트 저장, 복원, 공유 워크플로우

프로젝트 폴더 구조
------------------

역할 분담과 협업을 위해 프로젝트를 모듈 단위로 관리합니다.

```text
frontend/   React 기반 사용자 인터페이스와 화면 구성 요소
backend/    API 서버, 인증, 프로젝트 저장, 데이터 처리 로직
docs/       워크플로우 다이어그램, 설계 문서, 회의 기록
```

백엔드 폴더별 역할
------------------

- `backend/app/` : FastAPI API 서버 코드, 클라이언트 요청 처리, 라우터와 서비스 연결.
- `backend/app/core/` : 앱 설정, 데이터베이스 연결, 보안, 공통 의존성 및 업로드 유틸리티.
- `backend/app/routers/` : API 경로 정의, 각 기능별 엔드포인트 구현.
- `backend/app/services/` : 문서 분석, AI 모델 호출, 변환/처리/임베딩/번역 등 비즈니스 로직.
- `backend/models/` : 요청/응답 스키마 및 데이터 모델 정의.
- `backend/main.py` : FastAPI 앱 진입점, 서버 초기화와 실행 설정.
- `backend/Dockerfile` / `requirements*.txt` : 도커 빌드와 파이썬 의존성 정의.

AI 문서 파싱과 질의응답 모델 처리는 현재 백엔드 서비스 모듈에서 관리하며, 필요하면 추후 `ai-service/`로 분리할 수 있습니다.

백엔드 실행
-----------

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

환경 변수는 `backend/.env.example`을 `backend/.env`로 복사해서 설정합니다. 로컬 개발에서는 `MONGO_URL=mongodb://localhost:27017`을 사용할 수 있고, Docker Compose 배포에서는 루트 `docker-compose.yml`이 `MONGO_URL=mongodb://mongo:27017`로 덮어씁니다.

백엔드 배포
-----------

백엔드는 React 정적 파일을 직접 서빙하지 않고 API만 제공합니다. EC2에서는 루트 `docker-compose.yml`로 FastAPI 백엔드와 MongoDB를 실행하고, Vercel 프론트엔드는 `VITE_API_BASE_URL`로 이 백엔드의 공개 주소를 호출합니다.

운영 환경에서는 최소한 아래 값을 실제 운영 값으로 변경합니다.

- `APP_ENV=production`
- `JWT_SECRET_KEY`
- `OPENAI_API_KEY` 또는 사용하는 LLM 키
- `GOOGLE_CLIENT_ID`
- `CORS_ORIGINS`

Vercel preview URL도 허용하려면 `CORS_ORIGIN_REGEX=https://.*\.vercel\.app`을 설정합니다. 고정 운영 도메인만 허용하려면 이 값은 비워두는 편이 좋습니다.

EC2 Docker 실행:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
docker compose up -d --build
```

파트별 환경 설정 가이드
-----------------------

각 폴더의 README 또는 문서에는 아래 내용을 정리합니다.

- 필수 요구 사항: 사용하는 언어 버전, 런타임, 패키지 매니저
- 환경 변수: 실제 값은 공유하지 않고 `.env.example`에 빈 값 또는 예시 값만 작성
- 실행 방법: 의존성 설치와 로컬 실행 명령을 간단히 정리
- 담당 범위: 해당 폴더가 맡는 기능과 주요 진입 파일 설명

보안 주의 사항
--------------

GitHub에는 실제 비밀값이나 운영 정보를 올리지 않습니다.

절대 커밋하지 않을 항목:

- API 키
- OAuth 클라이언트 값
- 세션/JWT 시크릿
- 데이터베이스 계정 또는 접속 문자열
- 운영 서버 주소, IP, 배포 명령
- 개인 액세스 토큰
- 실제 사용자 데이터 또는 업로드 문서

협업 및 Git 전략
----------------

팀 프로젝트의 일관성을 유지하기 위해 아래 규칙을 따릅니다.

- `main`: 운영 또는 제출용 안정 브랜치
- `develop`: 기능 통합 및 검증 브랜치
- `feature/기능명`: 기능별 작업 브랜치

커밋 메시지는 작업 영역을 앞에 표시합니다.

```text
[FE] 분석 화면 미리보기 개선
[BE] 프로젝트 저장 API 수정
[AI] 문서 분석 모델 프롬프트 개선
```

PR을 만들 때는 최소 1명의 팀원이 리뷰한 뒤 `develop`에 병합합니다.

문서화 및 커뮤니케이션
----------------------

- FigJam/Figma 워크플로우는 최신 상태로 유지합니다.
- 외부에 공개해도 되는 링크만 README에 배치합니다.
- 팀 전용 설계 링크는 접근 권한을 제한하고, 공개 저장소에는 민감한 세부 내용을 적지 않습니다.
- 환경 설정 오류와 자주 묻는 질문은 `docs/` 또는 각 폴더 README의 Troubleshooting 섹션에 기록합니다.

Troubleshooting
---------------

자주 발생하는 문제와 해결 방법은 팀 문서에 계속 누적합니다.

- 환경 변수 파일이 없는 경우 `.env.example`을 기준으로 로컬 전용 파일을 만듭니다.
- 의존성 설치 오류가 나면 각 파트의 런타임 버전을 먼저 확인합니다.
- 실행 중 오류가 반복되면 에러 메시지, 실행 위치, 사용한 브랜치를 함께 공유합니다.
