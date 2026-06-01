# PaperMate Backend

FastAPI로 만든 PaperMate 백엔드입니다. Docker 실행은 프로젝트 루트에서 합니다.

## Docker 실행

Docker Desktop을 켠 뒤 프로젝트 루트에서 실행합니다.

```bat
copy backend\.env.example backend\.env
docker compose up --build
```

브라우저는 아래 주소로 접속합니다.

```text
http://127.0.0.1:3000
```

백엔드 상태 확인 주소입니다.

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/api/ready
```

## 컨테이너 구성

```text
frontend  nginx로 React 빌드 파일 서빙, /api 요청을 backend로 프록시
backend   FastAPI + Uvicorn
mongo     MongoDB 7
```

## 백엔드만 직접 실행

Docker 없이 백엔드만 따로 확인할 때 사용합니다.

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## 기본 분석 엔진: BERT/Qwen Grounding

기본 빌드에 sentence-transformers, transformers, accelerate가 포함됩니다. Grounding은 단어/숫자 검증과 질문-문장 의미 유사도 재정렬을 함께 사용합니다.

```env
ENABLE_BERT_GROUNDING=true
BERT_GROUNDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
BERT_GROUNDING_THRESHOLD=0.62
BERT_GROUNDING_INSTRUCTION=Given an answer sentence, retrieve the most relevant source passage from the uploaded document.
```

모델을 불러오지 못하면 서버는 멈추지 않고 기존 단어 기반 grounding으로 돌아갑니다.

더 강한 다국어 임베딩이 필요하고 GPU 메모리가 충분하면 Qwen3 임베딩 모델로 바꿀 수 있습니다.

```env
ENABLE_BERT_GROUNDING=true
BERT_GROUNDING_MODEL=Qwen/Qwen3-Embedding-8B
BERT_GROUNDING_THRESHOLD=0.62
```

`Qwen3-Embedding-8B`는 8B 모델이라 CPU나 일반 노트북에서는 매우 느리거나 메모리가 부족할 수 있습니다. 로컬 개발 기본값은 가벼운 MiniLM으로 두고, 서버/GPU 환경에서 Qwen으로 전환하는 방식을 권장합니다.

## 기본 분석 엔진: KoBERTopic 스타일 주제 추출

KoBERTopic은 BERTopic을 한국어에 적용하기 위해 Mecab 토크나이저와 다국어 SBERT를 조합한 예제입니다. PaperMate는 이 아이디어를 참고해 문서 분석 결과에 `[문서 주제 후보]`를 추가합니다.

기본 빌드에 BERTopic과 scikit-learn이 포함됩니다.

```env
ENABLE_TOPIC_MODELING=true
TOPIC_MODEL_BACKEND=bertopic
TOPIC_MODEL_LIMIT=5
```

Windows나 작은 컨테이너에서 HDBSCAN/모델 로드가 실패할 수 있어, 실패 시 로컬 토큰 기반 주제 추출로 돌아갑니다.

참고: https://github.com/ukairia777/KoBERTopic

## LLM과 로컬 엔진의 관계

LLM을 사용해도 BERT/Qwen grounding과 KoBERTopic은 사라지지 않습니다. 로컬 엔진은 문서에서 근거 문장과 주제 후보를 먼저 고르고, LLM은 그 근거를 바탕으로 자연어 답변을 만듭니다. LLM 답변 뒤에는 grounding 검증을 한 번 더 거쳐 문서에 없는 수치나 주장을 줄입니다.

## 트리 구조

```text
backend/
  main.py                  FastAPI 앱 시작 파일
  requirements.txt         Python 패키지 목록
  .env.example             환경변수 예시 파일
  Dockerfile               백엔드 Docker 이미지 설정

  app/
    core/
      config.py            환경변수와 서버 설정
      database.py          MongoDB 연결과 인덱스
      deps.py              로그인 사용자 확인
      security.py          비밀번호 해시와 JWT 토큰
      uploads.py           업로드 파일 개수/용량 검사

    routers/
      auth.py              회원가입, 로그인, 계정 관리
      projects.py          프로젝트 저장, 조회, 삭제
      analysis.py          문서 분석 Q&A
      visuals.py           표, 그래프, 이미지, 마인드맵 생성
      visual_assets.py     시각화 보관함 저장
      shared_rooms.py      공유방 저장
      discussion_comments.py 공유방 댓글 저장
      project_threads.py   분석 대화 기록 저장
      project_files.py     파일 메타데이터 저장

    services/
      document_analysis.py 문서 텍스트 추출과 기본 분석
      grounding.py         문서 근거 검증과 BERT/Qwen 의미 유사도 검사
      llm_analysis.py      OpenAI/Gemini 호출 연결부
      topic_modeling.py    KoBERTopic 스타일 주제 후보 추출
      visual_buttons/      시각화 버튼별 생성 로직

  models/
    schemas.py             API 요청/응답 데이터 모양
```
