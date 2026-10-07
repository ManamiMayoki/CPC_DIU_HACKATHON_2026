# Build from the repository root (see docker-compose.yml): the engine imports ml/validation.py
FROM python:3.11-slim
WORKDIR /app
COPY graph-engine/requirements.txt graph-engine/requirements.txt
RUN pip install --no-cache-dir -r graph-engine/requirements.txt
COPY ml ml
COPY graph-engine graph-engine
COPY data data
WORKDIR /app/graph-engine
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
