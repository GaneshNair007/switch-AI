FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/app/linking_antigravity
WORKDIR /app
COPY requirements.txt requirements-discord.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-discord.txt \
    && groupadd --gid 10001 shipcourt \
    && useradd --uid 10001 --gid 10001 --no-create-home shipcourt \
    && mkdir -p /app/.runtime && chown shipcourt:shipcourt /app/.runtime
COPY server/ server/
COPY assets/ assets/
COPY data/ data/
COPY linking_antigravity/scope_guard/ linking_antigravity/scope_guard/
COPY deploy/container_smoke.py deploy/container_smoke.py
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"
CMD ["python", "-m", "server.main", "--serve", "--host", "127.0.0.1", "--port", "8080"]
