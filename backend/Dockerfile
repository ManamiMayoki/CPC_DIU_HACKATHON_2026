# Build from the repository root (see docker-compose.yml): the API shells out to
# backend/engine_adapter.py, which needs Python plus the ml/ and graph-engine/ code.
FROM node:20-bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY ml/requirements.txt ml/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r ml/requirements.txt
COPY backend/package*.json backend/
RUN cd backend && npm ci --omit=dev
COPY backend backend
COPY ml ml
COPY graph-engine graph-engine
COPY data data
COPY frontend/public/data/initial_state.json frontend/public/data/initial_state.json
WORKDIR /app/backend
ENV PORT=5000
EXPOSE 5000
CMD ["node", "src/server.js"]
