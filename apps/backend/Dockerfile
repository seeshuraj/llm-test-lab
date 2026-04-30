# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps only in builder layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY apps/backend/requirements.txt .
COPY packages/core-python /build/packages/core-python
COPY packages/sdk-python  /build/packages/sdk-python

# Install CPU-only torch first (avoids pulling 2GB CUDA wheel)
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# Install all other deps into /install prefix
RUN pip install --no-cache-dir \
    --prefix=/install \
    -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim

# Non-root user for security
RUN useradd --create-home appuser
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY apps/backend/ ./
COPY packages/core-python /packages/core-python
COPY packages/sdk-python  /packages/sdk-python

# Install editable packages in runtime (needed for -e installs)
RUN pip install --no-cache-dir -e /packages/core-python -e /packages/sdk-python

USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
