"""Prompt and multimodal input construction for LLM analysis."""

MAX_CONTEXT_CHARS = 400000
MAX_GEMINI_CONTEXT_CHARS = 24000
MIN_GEMINI_CONTEXT_CHARS = 8000
MAX_MULTIMODAL_IMAGES = 4


def clip_text(text: str, limit: int = MAX_CONTEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[문서가 길어 일부만 분석에 사용되었습니다.]"


def build_ranked_document_context(
    question: str,
    extracted_docs: list[dict],
    relevant_chunks: list[dict] | None = None,
    context_limit: int = MAX_CONTEXT_CHARS,
) -> str:
    blocks = []
    remaining = context_limit
    for index, chunk in enumerate(relevant_chunks or [], start=1):
        text = clip_text(chunk.get("text", ""), max(1200, min(5000, remaining)))
        if not text.strip() or remaining <= 0:
            continue
        source_label = chunk.get("source_label") or f"Chunk {chunk.get('chunk_index', '?')}"
        block = "\n".join(
            [
                f"[관련 구간 {index}]",
                f"파일명: {chunk.get('filename', 'unknown')}",
                f"출처: {source_label}",
                "본문:",
                text,
            ]
        )
        blocks.append(block)
        remaining -= len(block)
        if remaining <= 2000:
            break

    if blocks:
        return clip_text("\n\n".join(blocks), context_limit)

    for index, doc in enumerate(extracted_docs, start=1):
        if remaining <= 0:
            break
        text = clip_text(doc.get("text", ""), max(1200, remaining))
        blocks.append(
            "\n".join(
                [
                    f"[문서 {index}]",
                    f"파일명: {doc.get('filename', 'unknown')}",
                    f"형식: {doc.get('format', 'unknown')}",
                    "본문:",
                    text,
                ]
            )
        )
        remaining -= len(blocks[-1])
    return clip_text("\n\n".join(blocks), context_limit)


def multimodal_image_inputs(extracted_docs: list[dict], limit: int = MAX_MULTIMODAL_IMAGES) -> list[dict]:
    inputs = []
    for doc in extracted_docs or []:
        for asset in doc.get("visual_assets", []) or []:
            data_url = asset.get("data_url")
            if not data_url:
                continue
            label = asset.get("source_label") or asset.get("name") or "document image"
            inputs.append(
                {
                    "type": "image_url",
                    "image_url": {"url": data_url, "detail": "auto"},
                    "label": label,
                }
            )
            if len(inputs) >= limit:
                return inputs
    return inputs


def chat_user_content(user_prompt: str, extracted_docs: list[dict]):
    image_inputs = multimodal_image_inputs(extracted_docs)
    if not image_inputs:
        return user_prompt
    content = [{"type": "text", "text": user_prompt}]
    content.extend({"type": item["type"], "image_url": item["image_url"]} for item in image_inputs)
    return content


def is_visual_request(question: str) -> bool:
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
        "마인드맵",
        "비교표",
        "json",
        "visual",
        "chart",
        "table",
        "graph",
        "mindmap",
    )
    lowered = (question or "").lower()
    if any(
        keyword in (question or "")
        for keyword in (
            "표",
            "테이블",
            "그래프",
            "차트",
            "시각화",
            "막대",
            "선 그래프",
            "꺾은선",
            "원형",
            "마인드맵",
        )
    ):
        return True
    return any(keyword in lowered for keyword in visual_keywords)


def build_prompts(
    question: str,
    extracted_docs: list[dict],
    analysis_text: str = "",
    relevant_chunks: list[dict] | None = None,
    context_limit: int = MAX_CONTEXT_CHARS,
) -> tuple[str, str]:
    document_context = build_ranked_document_context(question, extracted_docs, relevant_chunks, context_limit)

    core_prompt = (
        "You are 'PaperMate', a top-tier AI research assistant designed to help users analyze and visualize various documents, including academic papers, business reports, and proposals.\n\n"
        "[Core Principles]\n"
        "1. Strict Grounding: You MUST base your answers SOLELY on the provided document (Context). Zero hallucination. Do not use external knowledge.\n"
        "2. Citation: Always append the precise source at the end of sentences when citing facts or numbers. For PDFs, cite only the provided source label like [File Name - Page X]. Never treat bracketed reference numbers such as [26] in a REFERENCES section as page numbers. For HWP/HWPX/DOCX, cite the provided section label. NEVER cite the [Previous Conversation History] as a source.\n"
        "3. Output Language: Always write final user-facing responses in Korean, regardless of the uploaded document language. If the source document is English or another language, translate and synthesize it into natural Korean. Keep proper nouns, model names, technical abbreviations, numbers, and citations as-is only when necessary. Chart labels and suggested questions MUST also be Korean.\n"
        "4. Reasoning Discipline: Before writing your final answer, deeply analyze the user's request and the document context step-by-step internally. Extract all necessary facts first, then synthesize them into a logical and highly accurate final response. Do not reveal hidden chain-of-thought; provide concise evidence summaries only when useful.\n\n"
    )

    text_mode_prompt = (
        "-----------------------------------\n"
        "[Task: 📝 Standard Text Summary & Q&A]\n"
        "- 🚨 Rule 1 [Scope Control - CRITICAL]: First, identify the exact SCOPE of the user's prompt. If the user asks for a specific section (e.g., '서론만', '결과만') or asks to elaborate on a specific point, you MUST act as a 'Laser Extractor'. Completely IGNORE the rest of the document. NEVER provide a full-document summary in this case.\n"
        "- 🔍 Rule 2 [Deep Dive]: If the user says '이 부분을 더 요약해줘' or '더 자세히 설명해줘', provide a highly detailed, focused analysis of ONLY that specific topic. Do not just skim.\n"
        "- 📝 Rule 3 [MANDATORY SUMMARY FORMAT]: When the user asks for a general summary, or when no specific scope is given, use the markdown structure below. Translate placeholders to Korean.\n\n"
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
        "- 🚨 Rule 4 [Full-Document Coverage]: If the document is short, extract every important detail without inventing filler text. For long documents, cover the middle and end sections as well, not only the abstract or introduction.\n"
        "- 🚨 Rule 5 [Mandatory Suggested Visualization Questions]: At the very end of your text response, you MUST append the exact separator '===SUGGESTED_QUESTIONS==='.\n"
        "After the separator, generate 3-4 highly recommended follow-up questions that guide the user to create tables or charts from data-rich sections in the document.\n"
        "Prioritize trends, comparisons, rankings, categories, time series, region/year/group breakdowns, and metrics that can be visualized.\n"
        "Do NOT recommend a visualization for a single isolated point in time. Prefer multi-period or multi-category questions such as monthly trends, yearly comparisons, regional comparisons, model comparisons, or before/after changes.\n"
        "Format each recommendation EXACTLY like this in Korean: '[추천 시각화: 95점] 2024년 분기별 매출 추이 꺾은선 그래프 그려줘'\n"
        "Do not include any other text after the separator except these formatted questions.\n"
    )

    visual_mode_prompt = (
        "-----------------------------------\n"
        "[Task: 📊 Data Visualization (Table/Chart/Mindmap)]\n"
        "- Auto-Routing: Analyze the data characteristics and independently decide the optimal visual format (table, bar, line, pie, mindmap).\n"
        "- [Year/Material Separation Rule - CRITICAL]: When the document has values by year, source file, material, region, experiment group, model, or category, those must be represented as separate chart series or separate table columns. Never merge them into one continuous line unless the user explicitly asks for a single combined timeline.\n"
        "- [Monthly Trend Rule - CRITICAL]: For monthly trend graphs, the X-axis MUST be the month labels such as '1월', '2월', ... '12월'. Each year must be a different series. Do NOT flatten the data into labels like '2024-03', '2025-03', '2026-03' on one line.\n"
        "- [Graph Request Priority]: If the user asks for a graph/chart, return type='chart' with chartType, xAxisKey, series, and data. Do not downgrade to a table just because the original data came from a table.\n"
        "- [Grounded Visual Data]: Every data value in the JSON must be directly extractable from the uploaded document context. If a month/year/source value is missing, use null rather than inventing a value.\n"
        "- 📊 [Data Extraction Rule]: For charts (bar, line, pie), you MUST extract multiple data points. DO NOT generate a chart with only a single data point on the X-axis.\n"
        "- 🚨 [STRICT JSON RULE]: When requested to visualize, you MUST return ONLY a single, raw JSON object. DO NOT include markdown code blocks, DO NOT add explanatory text outside the JSON, and DO NOT append 'SUGGESTED_QUESTIONS'.\n"
        "- [Renderer Responsibility Rule - CRITICAL]: Do NOT try to fully control final chart rendering details. The backend chart renderer will normalize data, validate keys, and build the final chart option.\n\n"
        "  [Strict JSON Format]\n"
        "  {\n"
        "    \"reasoning_summary\": \"시각화 선택 및 데이터 추출 근거를 한국어로 1~2문장만 간단히 작성하세요.\",\n"
        "    \"type\": \"chart\",\n"
        "    \"title\": \"그래프 제목\",\n"
        "    \"chartType\": \"line\",\n"
        "    \"template\": \"monthly_trend\",\n"
        "    \"xAxisKey\": \"month\",\n"
        "    \"columns\": [{\"key\": \"month\", \"label\": \"월\"}, {\"key\": \"value\", \"label\": \"값\"}],\n"
        "    \"series\": [{\"dataKey\": \"value\", \"name\": \"값\", \"yAxisId\": \"left\"}],\n"
        "    \"data\": [{\"month\": \"1월\", \"value\": 20000}]\n"
        "  }\n"
        "- 'type' MUST be one of: chart, table, mindmap.\n"
        "- 'chartType' MUST be one of: bar, line, pie if type is chart.\n"
        "- 'series' is required for charts except pie.\n"
    )

    system_prompt = core_prompt + (visual_mode_prompt if is_visual_request(question) else text_mode_prompt)
    history_block = f"[Previous Conversation History]\n{analysis_text}\n\n" if analysis_text else ""
    doc_block = f"[Uploaded Document Context]\n{document_context}\n\n" if document_context else ""

    if question and question.strip():
        user_prompt = f"""
[User Request]
{question}

{doc_block}{history_block}
Use the uploaded document context as the primary source. Use previous conversation history only to understand continuity, never as a citation source.
Important: Even if the uploaded document context is English, write the final analysis and summary in Korean.
"""
    else:
        user_prompt = f"""
[User Request]
문서의 전반적인 내용을 꼼꼼하게 분석해줘.

{doc_block}{history_block}
Use the uploaded document context as the primary source. Use previous conversation history only to understand continuity, never as a citation source.
Important: Even if the uploaded document context is English, write the final analysis and summary in Korean.
"""
    return system_prompt, user_prompt
