FROM python:3.13.5-slim

# バージョン情報のビルド引数（GitHub Actions reusable workflowから提供）
ARG VERSION=unknown
ARG BUILD_DATE=unknown
ARG COMMIT_SHA=unknown
ARG COMMIT_SHORT=unknown
ARG GITHUB_REF=unknown
ARG GITHUB_RUN_ID=unknown

# メタデータラベル（GitHub Actions reusable workflowと統合）
LABEL org.opencontainers.image.title="Twitter Bulk Blocker" \
      org.opencontainers.image.description="高度なキャッシュ戦略とバッチ処理を備えたエンタープライズグレードの大規模Twitter一括ブロックシステム" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.source="https://github.com/book000/twitter-bulk-blocker" \
      org.opencontainers.image.documentation="https://github.com/book000/twitter-bulk-blocker#readme" \
      org.opencontainers.image.url="https://github.com/book000/twitter-bulk-blocker" \
      org.opencontainers.image.vendor="book000" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.ref.name="${GITHUB_REF}" \
      org.label-schema.vcs-ref="${COMMIT_SHA}" \
      org.label-schema.vcs-url="https://github.com/book000/twitter-bulk-blocker.git" \
      org.label-schema.build-date="${BUILD_DATE}" \
      maintainer="book000"

WORKDIR /app

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tzdata && \
    ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    echo "Asia/Tokyo" > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# バージョン情報を環境変数として設定（version.pyから読み取り可能）
ENV DOCKER_VERSION="${VERSION}" \
    DOCKER_BUILD_DATE="${BUILD_DATE}" \
    DOCKER_COMMIT_SHA="${COMMIT_SHA}" \
    DOCKER_COMMIT_SHORT="${COMMIT_SHORT}" \
    GITHUB_REF="${GITHUB_REF}" \
    GITHUB_RUN_ID="${GITHUB_RUN_ID}" \
    TZ=Asia/Tokyo \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TWITTER_COOKIES_PATH=/data/cookies.json \
    TWITTER_USERS_FILE=/data/users.json \
    TWITTER_BLOCK_DB=/data/block_history.db \
    CACHE_DIR=/data/cache

COPY requirements.txt ./

RUN python -m pip install --no-cache-dir --upgrade pip==25.1.1 && \
    pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser twitter_blocker/ ./twitter_blocker/
COPY --chown=appuser:appuser README.md examples.md ./

USER appuser

VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)"

ENTRYPOINT ["python3", "-m", "twitter_blocker"]
CMD ["--help"]