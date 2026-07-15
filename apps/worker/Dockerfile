FROM python:3.12-slim

WORKDIR /app

COPY packages/secure_knowledge /packages/secure_knowledge
COPY apps/worker /app

RUN pip install --no-cache-dir /packages/secure_knowledge
RUN pip install --no-cache-dir .

CMD ["python", "-m", "src.main"]
