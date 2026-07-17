FROM python:3.12-slim

WORKDIR /app

COPY packages/secure-knowledge-core /packages/secure-knowledge-core
COPY apps/api /app

RUN pip install --no-cache-dir /packages/secure-knowledge-core
RUN pip install --no-cache-dir .

CMD ["uvicorn", "secure_knowledge_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
