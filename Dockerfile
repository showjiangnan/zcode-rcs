FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.11.5
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY zcode_rcs ./zcode_rcs
COPY web ./web
COPY sdk ./sdk
COPY protocol ./protocol
COPY README.md README.en.md LICENSE ./
RUN uv sync --frozen --no-dev && useradd --uid 10001 --create-home rcs && mkdir /data && chown rcs:rcs /data
USER rcs
ENV RCS_DATA_DIR=/data RCS_KEYS_FILE=/run/secrets/rcs_keys RCS_WEB_DIR=/app/web
EXPOSE 8030
CMD ["uv", "run", "--no-sync", "zcode-rcs", "serve", "--host", "0.0.0.0", "--port", "8030"]
