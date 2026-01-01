#!/bin/bash
# PBAP Admin Tool - Entrypoint
# ログディレクトリの権限を確認・修正

mkdir -p /app/logs
chmod 755 /app/logs

# Streamlitを起動（execでプロセス置換）
exec streamlit run src/main.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
