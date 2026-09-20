# The front end is built in one stage and served by the API in the next, so the image
# runs on a single port with no CORS and no second process.
FROM node:22-slim AS web

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim AS app

# PYTHONUNBUFFERED keeps container logs in real time. MINDFORGE_ROOT matters more than
# it looks: the package normally locates its data by walking up from its own __file__,
# which only lands in the right place for an editable install. Installed properly it
# sits in site-packages, so the root has to be stated.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MINDFORGE_ROOT=/app \
    STATIC_DIR=/app/static

WORKDIR /app

COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/src ./backend/src
RUN pip install --no-cache-dir ./backend

# The framework pack is the product of an offline ingestion run and is committed, so the
# image needs no API key to start serving the Framework page and no PDF to be built.
COPY backend/framework ./backend/framework
COPY backend/evals ./backend/evals
COPY --from=web /build/dist ./static

# Run as a non-root user; the writable paths it needs are created up front.
RUN useradd --create-home --uid 10001 mindforge \
    && mkdir -p /app/backend/framework/_cache /data \
    && chown -R mindforge:mindforge /app /data
USER mindforge

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "mindforge_assess.api:app", "--host", "0.0.0.0", "--port", "8000"]
