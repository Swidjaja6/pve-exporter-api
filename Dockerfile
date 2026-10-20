FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /bin/
WORKDIR /app

COPY pyproject.toml README.md uv.lock ./ 
RUN uv sync --frozen --no-dev --no-install-project   
COPY src ./src
RUN uv sync --frozen --no-dev           

RUN useradd --create-home exporter
USER exporter

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["homelab-api"]