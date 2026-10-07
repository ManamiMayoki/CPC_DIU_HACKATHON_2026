# Build from the repository root (see docker-compose.yml): the pipeline imports graph-engine/
FROM python:3.11-slim
WORKDIR /app
COPY ml/requirements.txt ml/requirements.txt
RUN pip install --no-cache-dir -r ml/requirements.txt
COPY ml ml
COPY graph-engine graph-engine
COPY data data
WORKDIR /app/ml
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001"]
