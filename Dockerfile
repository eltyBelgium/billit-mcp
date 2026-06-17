# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip build && \
    pip wheel --wheel-dir=/wheels .


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    BILLIT_BASE_URL=https://api.sandbox.billit.be

RUN useradd --create-home --uid 10001 billit
WORKDIR /home/billit

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

USER billit
EXPOSE 8000

# Default to HTTP transport; override the entrypoint args if you want stdio.
ENTRYPOINT ["billit-mcp"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
