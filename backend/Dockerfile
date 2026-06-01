FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# OCR 이미지 분석을 위해 Tesseract를 포함합니다.
# AI 연결 담당자가 LLM만 붙여도 기본 문서 추출/이미지 OCR은 같은 컨테이너에서 동작합니다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential tesseract-ocr tesseract-ocr-kor \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
