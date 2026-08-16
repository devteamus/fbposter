# ============================================================
# Stage 1: Build Next.js frontend as static export
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app

RUN apk add --no-cache libc6-compat

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund

# Copy frontend source
COPY frontend/ .

# Disable Next.js telemetry (no prompt)
RUN npx next telemetry disable || true

# Build static export → produces /app/out/
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ============================================================
# Stage 2: Python backend + bundled static frontend
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2 + Pillow (in case we add image handling later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy built static frontend from builder stage
RUN mkdir -p /app/static
COPY --from=frontend-builder /app/out /app/static

# Ensure data + uploads dirs exist with proper permissions
RUN mkdir -p /app/data /app/uploads && chmod -R 777 /app/data /app/uploads

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=5000

EXPOSE 5000

# Healthcheck using curl (lighter than spawning python)
HEALTHCHECK --interval=15s --timeout=10s --start-period=45s --retries=5 \
  CMD curl -fsS http://localhost:5000/api/health || exit 1

CMD ["python", "app.py"]
