FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl-cffi ships manylinux wheels with libcurl bundled, so no build toolchain is
# needed — only CA roots for outbound TLS to BookMyShow / District / TMDB.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py .

# The SQLite file lives on a mounted volume (/data) so watches, users and alert
# logs survive container rebuilds. Four slashes = absolute path.
ENV HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_URL=sqlite+aiosqlite:////data/ticket_fox_web.db

EXPOSE 8000

# No curl in the image; probe /health with the interpreter that is already here.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"

CMD ["python", "run.py"]
