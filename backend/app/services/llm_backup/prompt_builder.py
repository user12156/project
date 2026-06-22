"""Prompt and multimodal input construction for LLM analysis."""

import re

from app.services.analysis.query_analyzer import _intent_label, _question_intent


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


def build_web_context(web_docs: list[dict], context_limit: int = 12000) -> str:
    blocks = []
    remaining = context_limit
    for index, doc in enumerate(web_docs or [], start=1):
        if remaining <= 0:
            break
        text = clip_text(doc.get("text", ""), max(800, min(2500, remaining)))
        if not text.strip():
            continue
        block = "\n".join(
            [
                f"[웹 {index}]",
                f"제목: {doc.get('filename', '웹 검색 결과')}",
                f"URL: {doc.get('url', '')}",
                "내용:",
                text,
            ]
        )
        blocks.append(block)
        remaining -= len(block)
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
                    "image_url": {"url": data_url, "detail": "high"},
                    "label": label,
                }
            )
            if len(inputs) >= limit:
                return inputs
    return inputs


def multimodal_gemini_parts(extracted_docs: list[dict], limit: int = MAX_MULTIMODAL_IMAGES) -> list[dict]:
    parts = []
    for item in multimodal_image_inputs(extracted_docs, limit):
        data_url = (item.get("image_url") or {}).get("url", "")
        match = re.match(r"^data:(?P<mime>[-\w.+/]+);base64,(?P<data>.+)$", data_url)
        if not match:
            continue
        parts.append(
            {
                "inline_data": {
                    "mime_type": match.group("mime"),
                    "data": match.group("data"),
                }
            }
        )
    return parts


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
        "비교표",
        "json",
        "visual",
        "chart",
        "table",
        "graph",
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
    web_docs: list[dict] | None = None,
) -> tuple[str, str]:
    intent = _question_intent(question)
    document_context = build_ranked_document_context(question, extracted_docs, relevant_chunks, context_limit)
    web_context = build_web_context(web_docs or [])

    core_prompt = (
        "You are 'PaperMate', a top-tier AI research assistant designed to help users analyze and visualize various documents, including academic papers, business reports, and proposals.\n\n"
        "[Core Principles]\n"
        "1. Strict Grounding: By default, base answers SOLELY on the provided uploaded document context, which mirrors the user's preview panel. Zero hallucination. Do not use external knowledge, current events, or pretrained memory to fill gaps.\n"
        "1-1. Web Compare Exception: If and only if a [Web Search Context] block is provided, you may use it only for the user's explicit web-comparison request. Keep uploaded document facts separate from web facts and cite web facts with [웹 N].\n"
        "2. Citation: Always append the precise source at the end of sentences when citing facts or numbers. For PDFs, cite only the provided source label like [File Name - Page X]. Never treat bracketed reference numbers such as [26] in a REFERENCES section as page numbers. For HWP/HWPX/DOCX, cite the provided section label. NEVER cite the [Previous Conversation History] as a source.\n"
        "3. Output Language: Always write final user-facing responses in Korean, regardless of the uploaded document language. If the source document is English or another language, translate and synthesize it into natural Korean. Keep proper nouns, model names, technical abbreviations, numbers, and citations as-is only when necessary. Chart labels and suggested questions MUST also be Korean.\n"
        "4. Reasoning Discipline: Before writing your final answer, deeply analyze the user's request and the document context step-by-step internally. Extract all necessary facts first, then synthesize them into a logical and highly accurate final response. Do not reveal hidden chain-of-thought; provide concise evidence summaries only when useful.\n\n"
    )

    text_mode_prompt = (
        "-----------------------------------\n"
        "[Task: 📝 Standard Text Summary & Q&A]\n"
        "- 🚨 Rule 0 [Mode Priority]: Follow the detected request mode below. Mode-specific instructions override the generic summary format.\n"
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
        "(문서의 정보량을 최대한 보존할 수 있도록 H3 `###` 섹션을 풍부하게 생성하세요. 단, 시스템 최대 출력 한도를 초과하지 않도록 팩트 위주로 밀도 있게 작성하세요.)\n"
        "- 🚨 Rule 4 [Full-Document Coverage & Safety]: Extract every important detail, number, and conclusion from the provided chunks. Ensure you cover the middle and end sections. However, you MUST pace your output length to ensure you successfully print the '===SUGGESTED_QUESTIONS===' separator at the end before running out of tokens.\n"
        "- 🚨 Rule 5 [Dynamic Follow-Up Questions]: At the very end of your text response, you MUST append the exact separator '===SUGGESTED_QUESTIONS==='.\n"
        "After the separator, generate follow-up chips based ONLY on the numbers and facts you just wrote in your summary/analysis above. Do NOT search the whole document again.\n"
        "[Visual Quantity Rule]: You MUST maximize the number of visual recommendations based on the data available in your summary (Maximum 2).\n"
        "- If your summary contains multiple independent comparisons or rich data, you MUST generate EXACTLY 2 visual chips.\n"
        "- If your summary contains only limited data (e.g., just one comparison), generate EXACTLY 1 visual chip.\n"
        "- If your summary contains ZERO numbers or facts, generate 0 visual chips.\n"
        "🚨 [STRICT VISUAL RULE]: DO NOT suggest a visual chip UNLESS your summary explicitly contains multi-row tabular data (at least 2 distinct categories AND their exact paired numeric values). If your summary only discusses abstract trends or has only a single number, YOU MUST NOT suggest a visualization.\n"
        "After determining the number of visual chips, generate general related question chips to reach EXACTLY 4 chips in total.\n"
        "Format visual chips in natural Korean starting with the prefix '[추천 시각화]'. Use abstract phrasing asking for visualization. For example: '[추천 시각화] A와 B의 실적 비교를 시각화해 줘' or '[추천 시각화] X의 연도별 변화를 시각화해 볼까?'\n"
        "(CRITICAL: The visual recommendation text MUST naturally ask for a visualization. However, you MUST NOT include specific format words like '그래프', '막대그래프', '차트', '표', '도표' anywhere in the chip text.)\n"
        "Format related question chips EXACTLY like this in Korean: '[연관 질문] <구체적인 후속 질문 내용>'\n"
        "Do not include any other text after the separator except these formatted chips.\n"
    )

    intent_prompt = {
        "summary": (
            "[Detected Request Mode: SUMMARY]\n"
            "- The user wants a concise summary. Prioritize the whole-document gist, main topic, conclusion, and 3-5 key points.\n"
            "- Do NOT over-expand into a deep section-by-section analysis unless the document is very short.\n"
        ),
        "analysis": (
            "[Detected Request Mode: DEEP ANALYSIS]\n"
            "- The user wants analysis, not just summary. Explain structure, meaning, implications, evidence, and relationships between points.\n"
            "- Include sections such as '핵심 해석', '근거', '시사점', and '주의할 점' when supported by the document.\n"
        ),
        "importance": (
            "[Detected Request Mode: IMPORTANCE RANKING]\n"
            "- The user asks what is important or asks for importance. Rank the most important points by priority.\n"
            "- For each item, explain why it matters and cite the exact supporting source. Avoid a generic full-document summary.\n"
            "- Use a numbered list with importance labels such as '가장 중요', '중요', '보조 근거'.\n"
        ),
        "metrics": (
            "[Detected Request Mode: METRICS]\n"
            "- The user is asking about numbers, results, trends, or changes. Prioritize concrete values, units, periods, groups, and comparisons.\n"
            "- If the exact requested value is not present in the uploaded document context, say that it cannot be confirmed from the document instead of estimating or using outside knowledge.\n"
            "- Do not bury numeric evidence inside a broad summary.\n"
        ),
        "compare": (
            "[Detected Request Mode: COMPARISON]\n"
            "- The user wants comparison. Organize the answer by compared targets, commonalities, differences, and evidence.\n"
            "- If the targets are implicit, infer them only from the uploaded document context.\n"
        ),
        "extract": (
            "[Detected Request Mode: IMPORTANT SENTENCE EXTRACTION]\n"
            "- The user asks for important sentences or excerpts. Return selected source sentences/passages first, not a general summary.\n"
            "- For each excerpt, add a brief reason explaining why it is important and include the source label.\n"
            "- Preserve the wording of source passages as much as possible, but keep excerpts short.\n"
        ),
    }.get(intent, (
        "[Detected Request Mode: GENERAL]\n"
        "- Answer the user's question directly using the uploaded document context.\n"
    ))

    visual_mode_prompt = (
        "-----------------------------------\n"
        "[Task: 📊 Data Extraction for Visualization (Table Format)]\n"
        "- Auto-Routing: Your sole task is to extract numerical data from the document into a strict Table JSON format. The backend auto-charter will decide the final visual format (line, bar, pie) based on data dimensions.\n"
        "- [Grounded Visual Data]: Every data value in the JSON must be directly extractable from the uploaded document context. If a value is missing, use null rather than inventing a value.\n"
        "- 🚨 [STRICT JSON RULE]: When requested to visualize, you MUST return ONLY a single, raw JSON object. DO NOT include markdown code blocks, DO NOT add explanatory text outside the JSON, and DO NOT append 'SUGGESTED_QUESTIONS'.\n"
        "- [Recommended Chart]: You MUST intelligently choose the best chart type for the data in 'recommended_chart' ('line' for time-series/trends, 'pie' for 100% proportions, 'bar' for general comparisons).\n\n"
        "  [Strict JSON Format]\n"
        "  {\n"
        "    \"reasoning_summary\": \"데이터 추출 근거를 한국어로 1~2문장으로 간단히 작성하세요\",\n"
        "    \"type\": \"table\",\n"
        "    \"recommended_chart\": \"<line | bar | pie> (AI must evaluate and choose the best type)\",\n"
        "    \"title\": \"데이터 제목\",\n"
        "    \"columns\": [{\"key\": \"category\", \"label\": \"구분\"}, {\"key\": \"value\", \"label\": \"값\"}],\n"
        "    \"data\": [{\"category\": \"항목명\", \"value\": 20000}]\n"
        "  }\n"
        "- 'type' MUST always be 'table'.\n"
    )

    system_prompt = core_prompt + (visual_mode_prompt if is_visual_request(question) else text_mode_prompt + "\n" + intent_prompt)
    history_block = (
        "[Previous Conversation History - continuity only, not evidence]\n"
        f"{clip_text(analysis_text, 4000)}\n\n"
        if analysis_text
        else ""
    )
    doc_block = f"[Uploaded Document Context]\n{document_context}\n\n" if document_context else ""
    web_block = f"[Web Search Context]\n{web_context}\n\n" if web_context else ""

    if question and question.strip():
        user_prompt = f"""
[User Request]
{question}

[Detected Intent]
{intent} - {_intent_label(intent)}

{doc_block}{web_block}{history_block}
Answer the current user request directly. Do not repeat or summarize the previous answer unless the current request explicitly asks for repetition. Use the uploaded document context as the only factual source unless a Web Search Context block is present. If Web Search Context is present, use it only to compare with the uploaded document and clearly label web-derived facts. Use previous conversation history only to understand continuity, never as a citation source, data source, or answer template. If the answer is not directly supported by the uploaded document context or the explicit web context, say that it cannot be confirmed.
Important: Even if the uploaded document context is English, write the final analysis and summary in Korean.
"""
    else:
        user_prompt = f"""
[User Request]
문서의 전반적인 내용을 꼼꼼하게 분석해줘.

[Detected Intent]
analysis - {_intent_label("analysis")}

{doc_block}{web_block}{history_block}
Answer the current user request directly. Do not repeat or summarize the previous answer unless the current request explicitly asks for repetition. Use the uploaded document context as the only factual source unless a Web Search Context block is present. If Web Search Context is present, use it only to compare with the uploaded document and clearly label web-derived facts. Use previous conversation history only to understand continuity, never as a citation source, data source, or answer template. If the answer is not directly supported by the uploaded document context or the explicit web context, say that it cannot be confirmed.
Important: Even if the uploaded document context is English, write the final analysis and summary in Korean.
"""
    return system_prompt, user_prompt
