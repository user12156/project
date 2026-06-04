# 초보자 안내: OpenAI 또는 Gemini 같은 외부 AI API를 호출해 더 자연스러운 분석 답변을 만드는 서비스입니다.

<<<<<<< HEAD
import os

from ..core.config import settings



MAX_CONTEXT_CHARS = 400000
=======
import json
import os
import re

from app.core.config import settings


MAX_CONTEXT_CHARS = 100000
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10


def _clip(text: str, limit: int = MAX_CONTEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[문서가 길어 일부만 분석에 사용되었습니다.]"


<<<<<<< HEAD
def _build_relevant_chunk_context(relevant_chunks: list[dict] | None = None) -> str:
    chunks = relevant_chunks or []
    if not chunks:
        return ""

    lines = ["[질문 관련 근거 구간]"]
    for index, chunk in enumerate(chunks[:6], start=1):
        filename = chunk.get("filename", "unknown")
        source_label = chunk.get("source_label") or f"Chunk {chunk.get('chunk_index', index)}"
        score = chunk.get("score", "")
        text = _clip(str(chunk.get("text", "")), 1200)
        lines.append(f"{index}. {filename} / {source_label} / score={score}\n{text}")
    return "\n\n".join(lines)


=======
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
def _build_ranked_document_context(
    question: str,
    extracted_docs: list[dict],
    relevant_chunks: list[dict] | None = None,
) -> str:
<<<<<<< HEAD
=======
    # 🚨 [CRITICAL FIX]: Do NOT use rank_relevant_chunks (TF-IDF) when using LLMs.
    # The local chunking algorithm destroys the document structure and has a hardcoded bias
    # for numbers/metrics, which hides crucial parts like the Introduction from the AI.
    # GPT-4o-mini has a large enough context window to read the document directly.

>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    blocks = []
    for index, doc in enumerate(extracted_docs, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[문서 {index}]",
                    f"파일명: {doc.get('filename', 'unknown')}",
                    f"형식: {doc.get('format', 'unknown')}",
                    "본문:",
<<<<<<< HEAD
                    _clip(doc.get("text", ""), MAX_CONTEXT_CHARS),
=======
                    _clip(doc.get("text", ""), 6000),
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
                ]
            )
        )
    return _clip("\n\n".join(blocks))


def _is_visual_request(question: str) -> bool:
    visual_keywords = (
        "표",
        "테이블",
        "그래프",
        "차트",
        "시각화",
        "막대",
        "선형",
        "선 그래프",
        "꺾은선",
        "원형",
        "파이",
<<<<<<< HEAD
=======
        "마인드맵",
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        "비교표",
        "json",
        "visual",
        "chart",
        "table",
        "graph",
<<<<<<< HEAD
    )
    lowered = (question or "").lower()
    if any(keyword in (question or "") for keyword in ("표", "테이블", "그래프", "차트", "시각화", "막대", "선 그래프", "꺾은선", "원형")):
=======
        "mindmap",
    )
    lowered = (question or "").lower()
    if any(keyword in (question or "") for keyword in ("표", "테이블", "그래프", "차트", "시각화", "막대", "선 그래프", "꺾은선", "원형", "마인드맵")):
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        return True
    return any(keyword in lowered for keyword in visual_keywords)


<<<<<<< HEAD
=======
def _extract_nationwide_monthly_births(text: str) -> dict | None:
    """Extract the official nationwide monthly birth counts from population trend tables."""

    compact_text = re.sub(r"\s+", " ", text or "")
    start = compact_text.find("2023.12월")
    if start < 0:
        start = compact_text.find("2024. 1월")
    if start < 0:
        start = compact_text.find("2024.1월")
    if start < 0:
        return None

    end_candidates = [
        compact_text.find("2. 출생", start),
        compact_text.find("(단위: 명, %) 전 국", start),
    ]
    end_candidates = [index for index in end_candidates if index > start]
    end = min(end_candidates) if end_candidates else min(len(compact_text), start + 8000)
    source = compact_text[start:end]

    current_year = ""
    by_month: dict[int, dict] = {}
    row_pattern = re.compile(r"(?:(20\d{2}p?)\.\s*)?(\d{1,2})월\s+([0-9,]+)")

    for match in row_pattern.finditer(source):
        year, month_text, births_text = match.groups()
        if year:
            current_year = year
        if current_year not in {"2024", "2025p", "2026p"}:
            continue

        month = int(month_text)
        if not 1 <= month <= 12:
            continue

        birth_digits = births_text.replace(",", "")
        if re.fullmatch(r"\d{2},\d{2}", births_text):
            birth_digits += "0"
        row = by_month.setdefault(month, {"month": f"{month}월", "monthOrder": month})
        row[current_year] = int(birth_digits)

    data = [by_month[month] for month in sorted(by_month)]
    if not data:
        return None

    series = []
    for year, color in [("2024", "#94a3b8"), ("2025p", "#64748b"), ("2026p", "#0f172a")]:
        if any(row.get(year) is not None for row in data):
            series.append({"dataKey": year, "name": f"{year}년" if not year.endswith("p") else f"{year[:-1]}년p", "color": color, "yAxisId": "left"})

    return {
        "title": "전국 월별 출생아 수",
        "source": "인구동태건수 및 동태율 / 전국 월별 출생 추이",
        "chartType": "line",
        "xAxisKey": "month",
        "series": series,
        "data": data,
    }


def _build_structured_visual_context(question: str, extracted_docs: list[dict]) -> str:
    """Provide deterministic table data to the LLM when a known statistical table is requested."""

    q = question or ""
    if not _is_visual_request(q):
        return ""

    wants_birth_trend = (
        ("출생" in q or "출생아" in q)
        and ("월별" in q or "추이" in q or "전국" in q or "그래프" in q or "차트" in q)
    )
    if not wants_birth_trend:
        return ""

    for doc in extracted_docs or []:
        parsed = _extract_nationwide_monthly_births(doc.get("text", ""))
        if not parsed:
            continue
        parsed["filename"] = doc.get("filename", "unknown")
        return (
            "[Structured Visual Data - MUST USE THIS FOR THE CHART]\n"
            "The values below were parsed deterministically from the uploaded document table. "
            "When the user asks for nationwide monthly birth trend, use these exact values and do not infer replacements.\n"
            f"{json.dumps(parsed, ensure_ascii=False)}\n\n"
        )
    return ""


>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
def _build_prompts(
    question: str,
    extracted_docs: list[dict],
    analysis_text: str = "",
    relevant_chunks: list[dict] | None = None,
) -> tuple[str, str]:
    document_context = _build_ranked_document_context(question, extracted_docs, relevant_chunks)
<<<<<<< HEAD
=======
    structured_visual_context = _build_structured_visual_context(question, extracted_docs)
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10

    core_prompt = (
        "You are 'PaperMate', a top-tier AI research assistant designed to help users analyze and visualize various documents, including academic papers, business reports, and proposals.\n\n"
        "[Core Principles]\n"
        "1. Strict Grounding: You MUST base your answers SOLELY on the provided document (Context). Zero hallucination. Do not use external knowledge.\n"
        "2. Citation: Always append the precise source at the end of sentences when citing facts or numbers. For PDFs, cite only the provided source label like [File Name - Page X]. Never treat bracketed reference numbers such as [26] in a REFERENCES section as page numbers. For HWP/HWPX/DOCX, cite the provided section label. NEVER cite the [Previous Conversation History] as a source.\n"
        "3. Output Language: ALL user-facing responses, including chart labels and suggested questions, MUST be in Korean.\n"
<<<<<<< HEAD
        "4. Step-by-Step Reasoning (Chain of Thought): Before writing your final answer, deeply analyze the user's request and the document context step-by-step. Break down complex problems, extract all necessary facts first, and then synthesize them into a logical and highly accurate final response.\n\n"
=======
        "4. Reasoning Discipline: Before writing your final answer, deeply analyze the user's request and the document context step-by-step internally. Extract all necessary facts first, then synthesize them into a logical and highly accurate final response. Do not reveal hidden chain-of-thought; provide concise evidence summaries only when useful.\n\n"
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    )

    text_mode_prompt = (
        "-----------------------------------\n"
        "[Task: 📝 Standard Text Summary & Q&A]\n"
        "- 🚨 Rule 1 [Scope Control - CRITICAL]: First, identify the exact SCOPE of the user's prompt. If the user asks for a specific section (e.g., '서론만', '결과만') or asks to elaborate on a specific point, you MUST act as a 'Laser Extractor'. Completely IGNORE the rest of the document. NEVER provide a full-document summary in this case.\n"
        "- 🔍 Rule 2 [Deep Dive]: If the user says '이 부분을 더 요약해줘' or '더 자세히 설명해줘', provide a highly detailed, focused analysis of ONLY that specific topic. Do not just skim.\n"
<<<<<<< HEAD
        "- 📝 Rule 3 [MANDATORY SUMMARY FORMAT]: When the user asks for a general summary, or when no specific scope is given, use the markdown structure below. Translate placeholders to Korean.\n"
        "(⚠️ CRITICAL FOR MINI: If the user asks about a specific topic, DO NOT use this template. Write a free-form, highly detailed answer answering ONLY their specific question.)\n\n"
=======
        "- 📝 Rule 3 [MANDATORY SUMMARY FORMAT]: When the user asks for a general summary, or when no specific scope is given, use the markdown structure below. Translate placeholders to Korean.\n\n"
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        "## 🎯 핵심 요약\n"
        "(문서의 전체적인 핵심 내용을 1~2문단으로 명확하고 밀도 있게 요약. 두루뭉술한 표현 금지.)\n\n"
        "## 📚 주요 내용 상세 분석\n"
        "### 1. <주제명>\n"
        "* **<세부 지표/개념 1>:** (단순 요약이 아닌, 문서에 등장하는 구체적인 수치, 고유명사, 법령, 사실관계를 팩트 위주로 상세히 기재)\n"
        "* **<세부 지표/개념 2>:** (구체적인 팩트와 데이터 기재)\n"
        "* **주요 특징 및 세부사항:** (문서에서 강조하는 세부 통계, 기관명, 예시 등 구체적인 하위 데이터를 반드시 포함할 것)\n\n"
        "### 2. <주제명>\n"
        "* **<세부 지표/개념 1>:** ...\n"
        "(문서의 정보량을 최대한 보존할 수 있도록 H3 `###` 섹션을 풍부하게 생성하세요. '다수 포함되어 있다' 같은 모호한 표현을 절대 쓰지 말고, 정확히 어떤 내용인지 팩트 위주로 길고 상세하게 작성하세요.)\n"
<<<<<<< HEAD
        "- 🚨 Rule 4 [Anti-Laziness & Full-Document Coverage - CRITICAL]: You are prohibited from writing short, lazy summaries. If the document is short, extract every single detail without inventing filler text. However, for long documents (e.g., 40+ pages), you MUST comprehensively read all the way to the conclusion and appendix. Do not just summarize the abstract. For long documents, you MUST write an extremely detailed, exhaustive response (at least 1500-2000 words) extracting specific facts, numbers, and proper nouns from the middle and end as well.\n"
        "- 🚨 Rule 5 [Mandatory Suggested Questions - Visualizations]: At the very end of your text response, you MUST append the exact separator '===SUGGESTED_QUESTIONS==='.\n"
        "After the separator, you MUST generate 3-4 highly recommended questions for the user to ask you to draw tables or charts.\n"
        "Identify data-rich sections in the document suitable for visualization (e.g., trends, comparisons). Score them from 0 to 100 based on their importance, and sort them from highest to lowest.\n"
        "CRITICAL: NEVER recommend a visualization for a single point in time (e.g., '2026년 4월'). Always recommend trends or comparisons over multiple periods/categories (e.g., '월별 추이', '연도별 비교').\n"
        "Format each recommendation EXACTLY like this (in Korean): '[추천 시각화: 95점] 2024년 분기별 매출 추이 꺾은선 그래프 그려줘'\n"
        "Do not include any other text after the separator except these formatted questions.\n"
=======
        "- 🚨 Rule 4 [Mandatory Suggested Questions]: At the very end of your text response, you MUST append the exact separator '===SUGGESTED_QUESTIONS===' followed by 2-3 follow-up questions strictly based on the document.\n"
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    )

    visual_mode_prompt = (
        "-----------------------------------\n"
<<<<<<< HEAD
        "[Task: 📊 Data Visualization (Table/Chart)]\n"
        "- Auto-Routing: Independently decide the optimal visual format (table, bar, line, pie).\n"
        "- [Separation Rule]: When data has different categories (e.g., years, regions, models), represent them as separate chart series or table columns. Do NOT flatten them into one continuous line.\n"
        "- [Graph Priority]: If the user asks for a chart, return type='chart'. Do not downgrade to a table.\n"
        "- [Grounded Data]: Every value MUST be directly extractable from the uploaded context. Use null if missing.\n"
        "- [Data Extraction]: For charts, extract multiple data points to show a trend or comparison. Do not generate a chart with only a single X-axis data point. If there is only one data point available, you MUST use chartType='bar' instead of 'line'.\n"
        "- 🚨 [NUMERICAL DATA RULE]: ALL numerical values in the 'data' array MUST be raw numbers (e.g., 1000, 3.14). DO NOT use strings with commas or units (e.g., '1,000', '1천명' are FORBIDDEN). If you extract '1,000명', convert it to 1000.\n"
        "- 🚨 [STRICT JSON RULE]: You MUST return ONLY a single, raw JSON object. NO markdown code blocks (e.g., ```json), NO explanatory text, NO 'SUGGESTED_QUESTIONS'.\n"
        "- [Design Rule]: Simply use the example colors provided in the schema. DO NOT try to generate a new color palette.\n\n"
        "  [Strict JSON Format]\n"
        "  {\n"
        "    \"reasoning_summary\": \"시각화 추출 근거를 한국어로 1문장만 작성하세요.\",\n"
=======
        "[Task: 📊 Data Visualization (Table/Chart/Mindmap)]\n"
        "- Auto-Routing: Analyze the data characteristics and independently decide the optimal visual format (table, bar, line, pie, mindmap).\n"
        "- [Year/Material Separation Rule - CRITICAL]: When the document has values by year, source file, material, region, experiment group, model, or category, those must be represented as separate chart series or separate table columns. Never merge them into one continuous line unless the user explicitly asks for a single combined timeline.\n"
        "- [Monthly Trend Rule - CRITICAL]: For monthly trend graphs, the X-axis MUST be the month labels such as '1월', '2월', ... '12월'. Each year must be a different series, for example '2024년', '2025년p', '2026년p'. Do NOT flatten the data into labels like '2024-03', '2025-03', '2026-03' on one line.\n"
        "- [Graph Request Priority]: If the user asks for a graph/chart, return type='chart' with chartType, xAxisKey, series, and data. Do not downgrade to a table just because the original data came from a table.\n"
        "- [Grounded Visual Data]: Every data value in the JSON must be directly extractable from the uploaded document context. If a month/year/source value is missing, use null rather than inventing a value.\n"
        "- [Structured Data Priority]: If a [Structured Visual Data] block is provided in the user prompt, you MUST use that exact data for the chart. Do not replace it with nearby numbers from the raw text.\n"
        "- 📊 [Data Extraction Rule]: For charts (bar, line, pie), you MUST extract multiple data points (e.g., time series trends over several months/years, or comparisons across multiple categories). DO NOT generate a chart with only a single data point on the X-axis. If the document only has one data point, extract related metrics to form a comparison.\n"
        "- 🚨 [STRICT JSON RULE]: When requested to visualize, you MUST return ONLY a single, raw JSON object. DO NOT include markdown code blocks (e.g., ```json), DO NOT add any explanatory text outside the JSON, and DO NOT append 'SUGGESTED_QUESTIONS'.\n"
        "- 🎨 [Design Rule]: DO NOT blindly copy the example colors. Generate a fresh, context-aware color palette (HEX codes) for both 'theme' and 'series' that matches the document's vibe.\n"
        "- 📈 [Dual Axis Rule]: If the numerical scales of the data differ significantly, you MUST use a dual-axis by assigning 'yAxisId': 'left' to one series and 'right' to the other.\n\n"
        "  [Strict JSON Format (NO COMMENTS ALLOWED)]\n"
        "  {\n"
        "    \"reasoning_summary\": \"시각화 선택 및 데이터 추출 근거를 한국어로 1~2문장만 간단히 작성하세요.\",\n"
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        "    \"type\": \"chart\",\n"
        "    \"theme\": {\n"
        "      \"headerBackground\": \"#1e293b\",\n"
        "      \"headerTextColor\": \"#ffffff\",\n"
        "      \"cellBackground\": \"#f8fafc\",\n"
        "      \"cellTextColor\": \"#334155\",\n"
        "      \"borderColor\": \"#cbd5e1\"\n"
        "    },\n"
        "    \"chartType\": \"line\",\n"
        "    \"xAxisKey\": \"name\",\n"
        "    \"columns\": [\n"
        "      {\"key\": \"model\", \"label\": \"AI 모델\"},\n"
        "      {\"key\": \"score\", \"label\": \"정확도\"}\n"
        "    ],\n"
        "    \"series\": [\n"
<<<<<<< HEAD
        "      {\"dataKey\": \"score\", \"color\": \"#0ea5a4\", \"name\": \"정확도 점수\"},\n"
        "      {\"dataKey\": \"speed\", \"color\": \"#f59e0b\", \"name\": \"처리 속도\"}\n"
=======
        "      {\"dataKey\": \"score\", \"color\": \"#0ea5a4\", \"name\": \"정확도 점수\", \"yAxisId\": \"left\"},\n"
        "      {\"dataKey\": \"speed\", \"color\": \"#f59e0b\", \"name\": \"처리 속도\", \"yAxisId\": \"right\"}\n"
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        "    ],\n"
        "    \"data\": [\n"
        "      {\"name\": \"GPT-4\", \"model\": \"GPT-4\", \"score\": 95, \"speed\": 800000}\n"
        "    ]\n"
        "  }\n"
<<<<<<< HEAD
        "- 'type' MUST be one of: chart, table.\n"
        "- 'chartType' MUST be one of: bar, line, pie (only required if type is chart).\n"
        "- 'columns' is REQUIRED for tables.\n"
        "- 'series' is REQUIRED for ALL charts (including pie charts). You must specify the 'dataKey' mapping to the numerical value.\n"
=======
        "- 'type' MUST be one of: chart, table, mindmap.\n"
        "- 'chartType' MUST be one of: bar, line, pie (only required if type is chart).\n"
        "- 'columns' is required for tables. 'series' is required for charts.\n"
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    )

    if _is_visual_request(question):
        system_prompt = core_prompt + visual_mode_prompt
    else:
        system_prompt = core_prompt + text_mode_prompt

    history_block = f"[Previous Conversation History]\n{analysis_text}\n\n" if analysis_text else ""
<<<<<<< HEAD
    doc_block = f"[Uploaded Document Context]\n{document_context}\n\n" if document_context else ""
=======
    doc_block = f"{structured_visual_context}[Uploaded Document Context]\n{document_context}\n\n" if document_context else structured_visual_context
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10

    if question and question.strip():
        user_prompt = f"""
[User Request]
{question}

{doc_block}{history_block}
<<<<<<< HEAD
---
🚨 AI REMINDER: 
Please execute the [User Request] exactly: "{question}". 
If the request is about a specific section, DO NOT summarize the whole document. Focus ONLY on the requested part.
Note: If the request asks to modify a visual asset, prioritize the [Previous Conversation History].
=======
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
Use the uploaded document context as the primary source. Use previous conversation history only to understand continuity, never as a citation source.
"""
    else:
        user_prompt = f"""
<<<<<<< HEAD
{doc_block}{history_block}Please conduct a thorough and insightful analysis of the [Uploaded Document Context] based on its nature. Follow the formatting and structural guidelines provided in your system instructions.
=======
[User Request]
문서의 전반적인 내용을 꼼꼼하게 분석해줘.

{doc_block}{history_block}
Use the uploaded document context as the primary source. Use previous conversation history only to understand continuity, never as a citation source.
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
"""
    return system_prompt, user_prompt


def _llm_error(message: str, provider: str, model: str | None = None) -> dict:
    return {
        "answer": "",
        "llm_used": False,
        "provider": provider,
        "model": model,
        "llm_error": message,
    }


def _parse_suggested_questions(answer: str) -> tuple[str, list[str]]:
    parts = answer.split("===SUGGESTED_QUESTIONS===")
    main_answer = parts[0].strip()
    questions = []
    if len(parts) > 1:
        raw_qs = parts[1].strip().split("\n")
        for q in raw_qs:
            cleaned = q.strip().lstrip("-").lstrip("*").lstrip("0123456789. ").strip()
            if cleaned:
                questions.append(cleaned)
    return main_answer, questions


<<<<<<< HEAD
def _chunk_text(text: str, chunk_size: int = 30000) -> list[str]:
    # HWP files often have excessive whitespace, which slows down the LLM
    text = " ".join(text.split())
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

def _extract_chunk_with_openai(chunk: str, api_key: str, model: str, question: str = "", is_visual: bool = False) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=90.0, max_retries=1)
        
        if is_visual:
            prompt = (
                "You are a strict data extraction assistant.\n"
                f"The user wants to generate a visualization based on the following request: '{question}'\n"
                "Extract ONLY the specific numerical data, tables, and exact facts from the text chunk below that are relevant to this request.\n"
                "Do NOT write long sentences. List the raw data clearly. If there is NO relevant data in this chunk, output nothing.\n"
                f"\n[Text Chunk]\n{chunk}"
            )
        else:
            prompt = (
                "You are a fast data extractor.\n"
                "Extract the most critical facts, numbers, and key concepts from the following text chunk.\n"
                "Summarize them concisely into a few bullet points. Do not write long paragraphs.\n"
                f"\n[Text Chunk]\n{chunk}"
            )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        print(f"Chunk extraction failed: {exc}")
        return ""

=======
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
def _analyze_with_openai(
    question: str,
    extracted_docs: list[dict],
    api_key: str,
    analysis_text: str = "",
    relevant_chunks: list[dict] | None = None,
) -> dict:
    try:
        from openai import OpenAI
<<<<<<< HEAD
        import concurrent.futures
=======
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    except ModuleNotFoundError:
        return _llm_error("openai 패키지가 설치되어 있지 않습니다.", "openai")

    model = settings.openai_model
<<<<<<< HEAD
    client = OpenAI(api_key=api_key, timeout=300.0, max_retries=0)
    system_prompt, user_prompt = _build_prompts(question, extracted_docs, analysis_text, relevant_chunks)

    # --- MAP-REDUCE LOGIC FOR GPT-4O-MINI ---
    question_lower = (question or "").strip().lower()
    is_general_summary = not question_lower or any(kw in question_lower for kw in ("요약", "분석", "정리", "핵심"))
    is_visual_req = _is_visual_request(question)
    raw_document_text = "\n\n".join(doc.get("text", "") for doc in extracted_docs)
    is_long_doc = len(raw_document_text) > 15000 and "mini" in model.lower()
    
    if is_long_doc and (is_general_summary or is_visual_req):
        chunks = _chunk_text(raw_document_text, 30000)
        extracted_pieces = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # We must preserve the order of chunks to maintain logical flow
            future_to_index = {executor.submit(_extract_chunk_with_openai, chunk, api_key, model, question, is_visual_req): i for i, chunk in enumerate(chunks)}
            results = [None] * len(chunks)
            for future in concurrent.futures.as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    results[idx] = result
                except Exception:
                    results[idx] = ""
            
        extracted_pieces = [r for r in results if r]
        stitched_extraction = "\n\n---\n\n".join(extracted_pieces)
        doc_block = f"[Uploaded Document Context (Extracted Facts)]\n{stitched_extraction}\n\n"
        history_block = f"[Previous Conversation History]\n{analysis_text}\n\n" if analysis_text else ""
        
        if is_visual_req:
            user_prompt = f"{doc_block}{history_block}The user requested a visualization: '{question}'. Please output ONLY the strict JSON format as specified in your system instructions based on the extracted data above."
        else:
            user_prompt = f"{doc_block}{history_block}Please conduct a thorough and insightful analysis based on the extracted facts above. Follow the formatting and structural guidelines provided in your system instructions. Make it extremely detailed and section-by-section."

=======
    client = OpenAI(api_key=api_key)
    system_prompt, user_prompt = _build_prompts(question, extracted_docs, analysis_text, relevant_chunks)

>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as exc:
        return _llm_error(f"OpenAI 호출 실패: {exc}", "openai", model)

    if not answer:
        return _llm_error("OpenAI가 빈 답변을 반환했습니다.", "openai", model)

    main_answer, questions = _parse_suggested_questions(answer)

    return {
        "answer": main_answer,
        "suggested_questions": questions,
        "llm_used": True,
        "model": model,
        "provider": "openai",
    }


def analyze_with_llm(
    question: str,
    extracted_docs: list[dict],
    openai_api_key: str | None = None,
    analysis_text: str = "",
    relevant_chunks: list[dict] | None = None,
) -> dict:
    api_key = openai_api_key or settings.openai_api_key
    if not api_key:
        return _llm_error("OpenAI API 키가 없어 기본 문서 추출로 응답했습니다.", "openai")
    return _analyze_with_openai(question, extracted_docs, api_key, analysis_text, relevant_chunks)


def generate_chat_title(
    question: str,
    openai_api_key: str | None = None,
    analysis_text: str = ""
) -> str:
    """사용자의 첫 질문을 바탕으로 3~5단어의 짧은 제목을 생성합니다."""
    prompt = f"다음 질문(또는 분석 요청)을 바탕으로 대화방의 제목을 3~5단어 내외의 짧은 명사형으로 작성해.\n\n질문: {question}\n\n오직 제목만 출력할 것."

    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return question[:20]
    
    try:
        from openai import OpenAI
<<<<<<< HEAD
        client = OpenAI(api_key=api_key, timeout=300.0, max_retries=0)
=======
        client = OpenAI(api_key=api_key)
>>>>>>> 668b885c33dfb63e222feb660e03e2de50a9de10
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=20
        )
        return response.choices[0].message.content.strip().replace('"', '').replace("'", "")
    except Exception:
        return question[:20]
