# This Dockerfile is NOT used by Railway
# Railway uses hrms_backend/Dockerfile via railway.toml
# This file is here only for local Docker builds from repo root

FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*
COPY hrms_backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
RUN useradd -m -u 1000 hrms && mkdir -p /app /app/logs /app/uploads && chown -R hrms:hrms /app
WORKDIR /app
RUN apt-get update && apt-get install -y libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /home/hrms/.local
COPY --chown=hrms:hrms hrms_backend/ ./
USER hrms
ENV PATH=/home/hrms/.local/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
