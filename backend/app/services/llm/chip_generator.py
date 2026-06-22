"""Generates visualization and related question chips from a summary text."""

import json
from app.core.config import settings
from app.services.llm.gemini_provider import call_gemini
from app.services.openai_client import OPENAI_STRUCTURED_TIMEOUT_SECONDS, make_openai_client
from app.services.analysis_pipeline import _extract_json_object

CHIP_GENERATOR_PROMPT = """
You are a Chief Data Visualization Analyst. Read the following document summary and extract potential visualization and follow-up questions.

[Rules]
1. Based ONLY on the numbers and facts present in the summary, generate visual question chips.
2. 🚨 [STRICT VISUAL RULE]: DO NOT suggest a visual chip UNLESS the summary explicitly contains multi-row tabular data (at least 2 distinct categories AND their exact paired numeric values). If the summary only discusses abstract trends or has only a single number, return an empty list for visual questions.
3. [Analyst Persona]: For visual chips, look for the most dramatic changes, sharp contrasts, or paradoxical trends. Weave this core insight naturally into the question itself.
4. Format visual chips in natural Korean starting with the prefix '[추천 시각화]'. Use abstract phrasing asking for visualization. (e.g., '[추천 시각화] A와 B의 실적 비교를 시각화해 줘'). DO NOT use words like '그래프', '차트', '표', '도표'.
5. Generate general related question chips starting with '[연관 질문]'.
6. You MUST return exactly one valid JSON object. Do not add markdown blocks or explanations.

[JSON Schema]
{
  "visual_questions": ["[추천 시각화] ...", ...],
  "general_questions": ["[연관 질문] ...", ...]
}
"""

def generate_chips(
    summary_text: str,
    provider: str,
    openai_api_key: str | None = None,
    google_api_key: str | None = None,
) -> tuple[list[str], list[str]]:
    if not summary_text.strip():
        return [], []

    user_prompt = f"Summary:\n{summary_text}\n\nReturn JSON ONLY."

    try:
        if provider in {"gemini", "google"}:
            api_key = google_api_key or settings.gemini_api_key or settings.google_api_key
            if api_key:
                response = call_gemini(api_key, settings.gemini_model, CHIP_GENERATOR_PROMPT, user_prompt)
            else:
                return [], []
        else:
            api_key = openai_api_key or settings.openai_api_key
            if api_key:
                client = make_openai_client(api_key, OPENAI_STRUCTURED_TIMEOUT_SECONDS)
                # Ensure we use a mini/fast model for this small task if possible
                model = settings.openai_model
                if "gpt-4o" in model and "mini" not in model:
                    model = "gpt-4o-mini"
                    
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": CHIP_GENERATOR_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                response = resp.choices[0].message.content
            else:
                return [], []

        parsed = _extract_json_object(response) or {}
        visual_questions = parsed.get("visual_questions", [])
        general_questions = parsed.get("general_questions", [])
        
        return (
            [str(q) for q in visual_questions if str(q).startswith("[추천 시각화]")],
            [str(q) for q in general_questions if str(q).startswith("[연관 질문]")],
        )
    except Exception as e:
        print(f"Chip generation failed: {e}")
        return [], []
