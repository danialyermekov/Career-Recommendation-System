FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./

ARG REACT_APP_API_URL=
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ /app/backend/
RUN python -m pip install --upgrade --retries 10 --timeout 180 pip setuptools wheel \
    && python -m pip install --retries 10 --timeout 180 --prefer-binary --no-build-isolation /app/backend

COPY --from=frontend-builder /app/frontend/build /app/frontend/build

EXPOSE 8000

WORKDIR /app/backend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
