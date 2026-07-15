FROM python:3.12-slim

WORKDIR /app

COPY packages/secure_knowledge /packages/secure_knowledge
COPY apps/api /app

RUN pip install --no-cache-dir /packages/secure_knowledge
RUN pip install --no-cache-dir .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
