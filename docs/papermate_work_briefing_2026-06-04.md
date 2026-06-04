# PaperMate 작업 브리핑

작성일: 2026-06-04  
범위: 2026-06-03 ~ 2026-06-04 작업 내용  
목적: PPT 제작용 기능/함수/연동 결과 정리

## 1. 전체 작업 요약

이번 작업은 분석 페이지의 사용 흐름을 안정화하고, 문서 분석 결과를 시각화 버튼과 자연스럽게 연결하는 데 초점을 두었다.

주요 개선 영역은 다음과 같다.

- 원본 미리보기 유지 및 복원 안정화
- PDF/HWP/HWPX 동시 사용 시 미리보기 사라짐 방지
- 새 채팅/새분석 초기화 동작 정리
- 채팅창 클립 메뉴 및 시각화 버튼 연동
- 표 만들기 버튼을 GPT 분석 결과 기반으로 개선
- 표 컬럼명을 `목차내용`에서 `중요내용`으로 변경
- 문서 제목 자동 추출 로직 개선

## 2. 화면 흐름 구조

사용자는 `Home.tsx`의 사이드 메뉴 또는 프로젝트/최근 대화에서 분석 페이지로 진입한다.

분석 페이지의 핵심 컴포넌트는 `AnalysisC`이다.

주요 파일:

- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/Analysis.tsx`
- `frontend/src/services/api.ts`
- `backend/app/routers/analysis.py`
- `backend/app/routers/visuals.py`
- `backend/app/services/document_analysis.py`
- `backend/app/services/visual_buttons/table_visual.py`

## 3. 새 채팅 초기화 기능

### 목적

사이드 메뉴의 `새 채팅`을 눌렀을 때 분석 채팅창, 원본 미리보기, 선택 파일, 시각화 결과가 한 번에 초기화되도록 수정했다.

### 프론트 함수

#### `handleMenuRouting(menuName)`

위치: `frontend/src/pages/Home.tsx`

역할:

- 사이드 메뉴 클릭을 처리한다.
- `새 채팅` 클릭 시 `newAnalysisSignal` 값을 증가시킨다.
- 분석 페이지를 새 세션 key로 다시 렌더링한다.

연동:

- `setNewAnalysisSignal((prev) => prev + 1)`
- `setAnalysisSessionKey(...)`
- `navigateToView(VIEW.ANALYSIS, { clearRestoredData: true })`

결과:

- `AnalysisC`에 새 채팅 신호가 전달된다.
- 분석 페이지 내부의 리로드 버튼 동작과 같은 초기화가 실행된다.

#### `AnalysisC({ newAnalysisSignal })`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 분석 페이지 전체 상태를 관리하는 메인 컴포넌트이다.
- `newAnalysisSignal` prop을 감지한다.

연동:

- `useEffect(() => { handleNewAnalysis(); }, [newAnalysisSignal])`

결과:

- 외부 메뉴의 `새 채팅`과 내부 새분석 버튼이 같은 초기화 로직을 사용한다.

#### `handleNewAnalysis()`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 분석 페이지를 새 상태로 되돌린다.

초기화 항목:

- `files`
- `activeFiles`
- `messages`
- `visuals`
- `generatedVisuals`
- `selectedSourceKey`
- `sourcePreview`
- `sourcePreviewCache`
- `sourceObjectUrlsRef`
- `currentProject`
- `savedProjectId`

결과:

- 채팅창이 비워진다.
- 원본 미리보기가 비워진다.
- 이전 PDF/HWPX 변환 결과가 남지 않는다.
- 새 파일 업로드부터 다시 시작할 수 있다.

## 4. 원본 미리보기 유지 및 초기화

### 목적

페이지 새로고침, 프로젝트 이동, 최근 대화 복원, 새 채팅에서 원본 미리보기가 예측 가능하게 동작하도록 개선했다.

### 프론트 함수

#### `saveSourceFiles(ownerIds, files)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 사용자가 업로드한 실제 원본 파일 Blob을 IndexedDB에 저장한다.
- localStorage에는 파일명/크기 등 메타데이터만 저장되므로, 실제 미리보기 복원을 위해 별도 Blob 저장이 필요하다.

연동:

- `handleFileChange`
- `handleSendMessage`
- `persistProject`

결과:

- 페이지를 나갔다 돌아와도 원본 Blob을 다시 불러올 수 있다.

#### `loadSourceFiles(ownerIds)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- IndexedDB에서 저장된 원본 파일 Blob을 다시 읽는다.

연동:

- `restoreAnalysisSession`

결과:

- 프로젝트/최근 대화 복원 시 파일명뿐 아니라 실제 원본 파일을 다시 미리보기 영역에 올릴 수 있다.

#### `restoreAnalysisSession(sessionData)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 저장된 분석 세션을 복원한다.
- 채팅 기록, 시각화, 파일 목록, 프로젝트 정보를 다시 화면에 넣는다.

연동:

- `loadSourceFiles`
- `normalizeRestoredThread`
- `dedupeVisuals`

결과:

- 최근 대화 또는 프로젝트에서 분석 페이지로 돌아왔을 때 이전 분석 상태가 복원된다.
- 실제 원본 Blob이 있으면 원본 미리보기도 복원된다.

#### `cacheSourcePreview(fileKey, preview)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 파일별 미리보기 결과를 메모리 캐시에 저장한다.
- PDF, 이미지, 텍스트, HWP/HWPX 변환 PDF 결과를 재사용한다.

연동:

- 원본 미리보기 effect
- `analysisAPI.previewDocument`

결과:

- PDF/HWP/HWPX 여러 개를 띄워도 미리보기가 서로 덮어쓰이지 않는다.
- 탭 전환 시 미리보기 재생성이 줄어든다.

#### `sourceResetVersionRef`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 새 채팅 이후 이전 미리보기 비동기 작업이 다시 화면을 덮어쓰지 못하게 하는 버전 토큰이다.

연동:

- `handleNewAnalysis`
- 원본 미리보기 effect
- `analysisAPI.previewDocument`
- `loadSourceFiles`

결과:

- 새 채팅을 한 번 눌렀을 때 원본 미리보기가 즉시 사라진다.
- 이전 HWP/HWPX PDF 변환 결과가 늦게 도착해도 새 화면에 다시 나타나지 않는다.

## 5. HWP/HWPX 원본 미리보기 변환

### 목적

브라우저에서 직접 보기 어려운 HWP/HWPX 문서를 PDF 미리보기로 변환해 원본 미리보기 영역에 표시한다.

### 프론트 함수

#### `analysisAPI.previewDocument(file)`

위치: `frontend/src/services/api.ts`

역할:

- 파일을 `/api/analysis/preview`로 전송한다.
- 응답을 Blob PDF로 받는다.

연동:

- `Analysis.tsx` 원본 미리보기 effect
- 백엔드 `preview_document`

결과:

- HWP/HWPX 문서도 PDF iframe 형태로 미리볼 수 있다.

### 백엔드 함수

#### `preview_document(file)`

위치: `backend/app/routers/analysis.py`

역할:

- 프론트에서 받은 문서를 PDF 미리보기로 변환한다.

연동:

- `_get_preview_pdf`
- `_get_extracted_document`
- `render_text_preview_pdf`

결과:

- HWP/HWPX/PDF 기반 원본 미리보기용 PDF 응답을 생성한다.

#### `_get_extracted_document(filename, content)`

위치: `backend/app/routers/analysis.py`

역할:

- 같은 파일을 반복 분석하지 않도록 추출 결과를 캐싱한다.

연동:

- `extract_file_document`

결과:

- 미리보기와 분석 속도가 개선된다.

#### `_get_preview_pdf(filename, content)`

위치: `backend/app/routers/analysis.py`

역할:

- 추출된 문서 텍스트를 PDF 미리보기로 렌더링하고 캐싱한다.

연동:

- `_get_extracted_document`
- `render_text_preview_pdf`

결과:

- HWP/HWPX 변환 미리보기가 안정적으로 제공된다.

## 6. 문서 파싱 및 분석

### 백엔드 함수

#### `extract_file_document(filename, content)`

위치: `backend/app/services/document_analysis.py`

역할:

- 파일 확장자에 따라 문서 파서를 선택한다.
- PDF, HWPX, HWP, DOCX, TXT, 이미지 등을 처리한다.

연동:

- `analyze_chat`
- `create_visual`
- `_get_extracted_document`

결과:

- 업로드 문서에서 분석 가능한 텍스트와 미리보기 텍스트를 생성한다.

#### `build_analysis_answer(question, extracted_docs)`

위치: `backend/app/services/document_analysis.py`

역할:

- OpenAI 키가 없거나 LLM 호출이 실패했을 때 로컬 기본 분석을 만든다.
- 핵심 내용 요약, 중요 문장, 키워드, 수치 후보를 생성한다.

연동:

- `analyze_chat`
- `create_visual`

결과:

- API 키가 없어도 기본 분석 결과가 제공된다.

#### `analyze_chat(...)`

위치: `backend/app/routers/analysis.py`

역할:

- 채팅창 질문과 업로드 파일을 받아 분석 파이프라인에 전달한다.

연동:

- `extract_file_document`
- `run_analysis_pipeline`
- OpenAI/Gemini 키 입력값

결과:

- 채팅창에 분석 답변이 표시된다.
- 이후 표/그래프/이미지 만들기 버튼이 이 분석 답변을 활용한다.

## 7. 클립 메뉴 및 시각화 버튼

### 목적

채팅창 클립 버튼을 메뉴화하고, 파일 추가/이미지 만들기/그래프 만들기/표 만들기를 연결했다.

### 프론트 함수

#### `handleFileChange(event)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 사용자가 파일 선택창에서 파일을 고르면 파일 상태와 원본 미리보기를 갱신한다.
- 시각화 버튼에서 열린 파일 선택인지 일반 파일 추가인지 구분한다.

연동:

- `pendingVisualTypeRef`
- `handleCreateVisualFromFiles`
- `saveSourceFiles`

결과:

- 일반 파일 추가 시 채팅창에 `분석해 드릴까요?`가 입력된다.
- 시각화 버튼에서 파일을 선택하면 즉시 해당 시각화 생성 API를 호출한다.

#### `handleCreateVisualFromMenu(visualType)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 클립 메뉴의 이미지/그래프/표 버튼 클릭을 처리한다.
- 다음 파일 선택 결과가 어떤 시각화 요청인지 저장한다.

연동:

- `pendingVisualTypeRef`
- `fileInputRef.current.click()`

결과:

- 각 버튼 클릭 시 파일 추가창이 열린다.

#### `handleCreateVisualFromFiles(visualType, selectedFiles, nextActiveFiles)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 선택된 파일과 최근 분석 답변을 백엔드 시각화 API로 보낸다.

연동:

- `getLatestAnalysisText`
- `analysisAPI.createVisual`
- `setGeneratedVisuals`

결과:

- 채팅창과 시각화 보관함에 표/그래프/이미지가 생성된다.

#### `getLatestAnalysisText(messages)`

위치: `frontend/src/pages/Analysis.tsx`

역할:

- 최근 AI 답변 또는 시각화 텍스트 중 의미 있는 분석 내용을 찾는다.

연동:

- `handleCreateVisualFromFiles`

결과:

- 표 만들기가 원문을 따로 해석하기보다 기존 분석 결과를 우선 활용한다.

#### `analysisAPI.createVisual(type, files, analysisText, options)`

위치: `frontend/src/services/api.ts`

역할:

- `/api/visuals/{type}`로 파일, 분석 텍스트, provider 정보를 보낸다.

연동:

- `handleCreateVisualFromFiles`
- 백엔드 `create_visual`

결과:

- 표/그래프/이미지 생성 요청이 백엔드로 전달된다.

## 8. 표 만들기 GPT 연동

### 목적

표 버튼이 원문을 따로 해석해서 분석 결과와 어긋나는 문제를 줄이고, 이미 생성된 분석 답변을 GPT로 표 데이터로 변환하도록 개선했다.

### 백엔드 함수

#### `create_visual(visual_type, analysis_text, files, ...)`

위치: `backend/app/routers/visuals.py`

역할:

- 시각화 버튼 요청을 받는다.
- 파일을 파싱하고 분석 텍스트를 준비한다.
- `visual_type`에 맞는 생성 함수를 호출한다.

연동:

- `VISUAL_CREATORS`
- `extract_file_document`
- `build_analysis_answer`
- `create_table_visual`

결과:

- 프론트에서 요청한 표/그래프/이미지 데이터가 생성된다.

#### `create_table_visual(extracted_docs, analysis_text, openai_api_key=None)`

위치: `backend/app/services/visual_buttons/table_visual.py`

역할:

- 표 시각화 데이터를 생성하는 메인 함수이다.
- OpenAI 키가 있으면 GPT 표 생성을 우선 시도한다.
- 실패하면 분석 텍스트 기반 로컬 표 생성으로 fallback한다.

연동:

- `_gpt_table_from_analysis`
- `_source_lines`
- `_extract_structured_sections`
- `_document_title`

결과:

- `제목 / 중요내용 / 중요도(점수) / 정확도(%)` 컬럼의 와이드 표가 생성된다.

#### `_gpt_table_from_analysis(extracted_docs, analysis_text, openai_api_key=None)`

위치: `backend/app/services/visual_buttons/table_visual.py`

역할:

- OpenAI를 호출해 기존 분석 답변을 표 JSON으로 변환한다.
- 원문을 새로 해석하지 않고 분석 결과만 기준으로 삼도록 프롬프트를 구성한다.

연동:

- OpenAI API
- `_document_title`
- `_normalize_gpt_rows`

결과:

- 분석 답변과 더 일치하는 표가 생성된다.
- `llm_used=True`, `provider=openai`, `model=settings.openai_model` 정보가 결과에 포함된다.

#### `_normalize_gpt_rows(payload)`

위치: `backend/app/services/visual_buttons/table_visual.py`

역할:

- GPT가 반환한 JSON 행을 내부 표 형식으로 정규화한다.

처리 항목:

- `toc`
- `content`
- `importance`
- `accuracy`

결과:

- 프론트 `DynamicVisualizer`가 바로 렌더링할 수 있는 표 데이터가 된다.

#### `_document_title(extracted_docs)`

위치: `backend/app/services/visual_buttons/table_visual.py`

역할:

- 문서 제목을 자동 추출한다.
- `[Page 1]`, 저자명, 이메일, 학교명, 영어 부제 등을 제외하고 실제 제목 후보를 고른다.

연동:

- `_title_candidate_score`
- `_filename_title`

결과:

- 표 제목과 안내 문구에 실제 문서 제목이 들어간다.

#### `_title_candidate_score(line, index)`

위치: `backend/app/services/visual_buttons/table_visual.py`

역할:

- 문서 앞부분의 각 줄을 제목 후보로 점수화한다.

가점/감점 기준:

- 한글 제목
- 연구/분석/동향/방안 등 제목성 단어
- 위치가 앞쪽인지
- 페이지 표시/저자/이메일/초록/서론 같은 비제목 요소인지

결과:

- 문서마다 키워드를 수동 입력하지 않아도 제목을 유동적으로 잡는다.

## 9. 표 결과 구조

표 만들기 결과는 다음 구조로 프론트에 전달된다.

```json
{
  "type": "table",
  "title": "문서 제목",
  "text": "문서 제목을 표로 정리하였습니다.",
  "columns": [
    { "key": "toc", "label": "제목" },
    { "key": "content", "label": "중요내용" },
    { "key": "importance", "label": "중요도(점수)" },
    { "key": "accuracy", "label": "정확도(%)" }
  ],
  "data": [
    {
      "toc": "요약",
      "content": "핵심 내용 요약",
      "importance": 98,
      "accuracy": 90
    }
  ],
  "layout": {
    "aspectRatio": "10 / 6",
    "variant": "wide"
  }
}
```

결과:

- 사용자는 문서 전체 내용을 와이드 표로 한눈에 확인할 수 있다.
- `중요내용` 컬럼이 문서의 핵심 주장/근거/결론을 담는다.

## 10. 기능별 연동 요약표

| 기능 | 프론트 함수 | 백엔드 함수 | 결과 |
|---|---|---|---|
| 파일 추가 | `handleFileChange` | `extract_file_document` | 파일 업로드 후 분석 준비 |
| 원본 저장 | `saveSourceFiles` | 없음 | IndexedDB에 실제 Blob 저장 |
| 원본 복원 | `loadSourceFiles`, `restoreAnalysisSession` | 없음 | 페이지 이동 후 원본 미리보기 복원 |
| HWP/HWPX 미리보기 | `analysisAPI.previewDocument` | `preview_document`, `_get_preview_pdf` | HWP/HWPX를 PDF로 표시 |
| 새 채팅 | `handleMenuRouting`, `handleNewAnalysis` | 없음 | 채팅/파일/미리보기/시각화 초기화 |
| 표 만들기 | `handleCreateVisualFromFiles` | `create_visual`, `create_table_visual` | 분석 결과 기반 표 생성 |
| GPT 표 변환 | `analysisAPI.createVisual` | `_gpt_table_from_analysis` | 분석 답변과 일치하는 표 JSON 생성 |
| 제목 자동 추출 | 없음 | `_document_title`, `_title_candidate_score` | 문서별 실제 제목 표시 |

## 11. PPT 구성 제안

### 슬라이드 1. 프로젝트 개선 개요

- PaperMate 분석 페이지 안정화
- 원본 미리보기 복원
- 시각화 버튼 연동
- GPT 기반 표 생성

### 슬라이드 2. 전체 아키텍처

- `Home.tsx`
- `Analysis.tsx`
- `api.ts`
- FastAPI Router
- Document Analysis Service
- Visual Button Service

### 슬라이드 3. 새 채팅 초기화 흐름

1. `handleMenuRouting("새 채팅")`
2. `newAnalysisSignal` 증가
3. `AnalysisC`에서 신호 감지
4. `handleNewAnalysis()`
5. 채팅/파일/미리보기/시각화 초기화

### 슬라이드 4. 원본 미리보기 복원 흐름

1. 파일 업로드
2. `saveSourceFiles`
3. IndexedDB에 Blob 저장
4. 페이지 복귀
5. `restoreAnalysisSession`
6. `loadSourceFiles`
7. 원본 미리보기 표시

### 슬라이드 5. HWP/HWPX 미리보기 변환

1. `analysisAPI.previewDocument`
2. `preview_document`
3. `_get_extracted_document`
4. `_get_preview_pdf`
5. PDF iframe 표시

### 슬라이드 6. 표 만들기 버튼 흐름

1. 클립 메뉴 `표 만들기`
2. `handleCreateVisualFromMenu`
3. 파일 선택
4. `handleCreateVisualFromFiles`
5. `analysisAPI.createVisual`
6. `create_visual`
7. `create_table_visual`

### 슬라이드 7. GPT 표 생성 로직

1. 최근 분석 답변 추출
2. `_gpt_table_from_analysis`
3. OpenAI 호출
4. `_normalize_gpt_rows`
5. `중요내용` 중심 표 생성

### 슬라이드 8. 개선 결과

- 새 채팅 한 번으로 완전 초기화
- 원본 미리보기 사라짐/잔상 문제 개선
- PDF/HWP/HWPX 동시 작업 안정화
- 분석 답변과 표 내용의 일치도 개선
- 문서별 제목 자동 추출

## 12. 발표용 한 문장 요약

이번 개선은 PaperMate의 분석 페이지에서 문서 업로드, 원본 미리보기, 분석 답변, 시각화 생성이 끊기지 않고 이어지도록 연결한 작업이며, 특히 표 만들기 기능은 GPT가 기존 분석 결과를 기반으로 `중요내용` 중심의 와이드 표를 생성하도록 개선했다.
