FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# OCR 이미지 분석과 HWP/HWPX 파싱 기반 PDF 미리보기를 위해 Tesseract와 한글 폰트를 포함합니다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential tesseract-ocr tesseract-ocr-kor fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.docker.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
