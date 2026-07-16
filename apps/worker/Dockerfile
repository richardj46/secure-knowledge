FROM python:3.12-slim

WORKDIR /app

COPY packages/secure-knowledge-core /packages/secure-knowledge-core
COPY apps/worker /app

RUN pip install --no-cache-dir /packages/secure-knowledge-core
RUN pip install --no-cache-dir .

CMD ["celery", "-A", "secure_knowledge_worker.celery_app:celery_app", "worker", "--loglevel=INFO", "--concurrency=2"]
