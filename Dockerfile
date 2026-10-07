# Stage 1: Build React frontend
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./

ARG REACT_APP_API_URL=
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

RUN npm run build


# Stage 2: Python runtime
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app/backend

# Install system dependencies (libgomp1 is required by LightGBM and CatBoost OpenMP runtime)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency specifications and lockfile for layer caching
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./

# Install locked dependencies without dev packages and without installing project package
RUN uv sync --locked --no-dev --no-install-project

# Add virtual environment to PATH
ENV PATH="/app/backend/.venv/bin:$PATH"

# Copy backend source code, required ML artifacts and runtime datasets
COPY backend/ ./

# Install project package into virtual environment using locked metadata
RUN uv sync --locked --no-dev --no-editable

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/frontend/build /app/frontend/build

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
