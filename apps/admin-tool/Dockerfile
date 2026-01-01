# PBAP Admin Tool - Dockerfile
# Streamlit + OpenCV ベースのイメージ

FROM python:3.11-slim

# 環境変数設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OpenCV依存のシステムライブラリ + curl（ヘルスチェック用）をインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxext-dev \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /app

# 依存関係インストール（キャッシュ効率化のため先にコピー）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY src/ ./src/

# 非rootユーザー作成・切り替え
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

# エントリーポイントスクリプト（ユーザー作成後にコピー）
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser

# ログディレクトリ作成（entrypoint内でも実行）
RUN mkdir -p /app/logs && chmod 755 /app/logs

ENTRYPOINT ["/app/entrypoint.sh"]

# Streamlitポート
EXPOSE 8501

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1
