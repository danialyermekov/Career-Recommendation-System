# Stage 1: Build React frontend
FROM node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./

ARG REACT_APP_API_URL=
ARG REACT_APP_SUPABASE_URL
ARG REACT_APP_SUPABASE_PUBLISHABLE_KEY
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
ENV REACT_APP_SUPABASE_URL=${REACT_APP_SUPABASE_URL} \
    REACT_APP_SUPABASE_PUBLISHABLE_KEY=${REACT_APP_SUPABASE_PUBLISHABLE_KEY}

RUN node -e 'if (!process.env.REACT_APP_SUPABASE_URL || !process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY) process.exit(1)' && npm run build


# Stage 2: Python runtime
FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS runtime

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
COPY --from=ghcr.io/astral-sh/uv@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /bin/uv

# Copy dependency specifications and lockfile for layer caching
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./

# Install locked dependencies without dev packages and without installing project package
RUN --mount=type=cache,target=/root/.cache/uv UV_CONCURRENT_DOWNLOADS=4 uv sync --locked --no-dev --no-install-project

# Add virtual environment to PATH
ENV PATH="/app/backend/.venv/bin:$PATH"

# Copy backend source code, required ML artifacts and runtime datasets
COPY backend/ ./

# Install project package into virtual environment using locked metadata
RUN --mount=type=cache,target=/root/.cache/uv UV_CONCURRENT_DOWNLOADS=4 uv sync --locked --no-dev --no-editable

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/frontend/build /app/frontend/build

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
