#!/usr/bin/env bash

set -e

echo "=============================="
echo "Starting AI Environment"
echo "=============================="

echo "[1/2] Starting Open WebUI container..."
docker start open-webui >/dev/null 2>&1 || true

sleep 2

echo "[2/2] Starting Cloudflare tunnel..."
pkill cloudflared >/dev/null 2>&1 || true

cloudflared tunnel run cics-tunnel &

sleep 3

echo "=============================="
echo "Environment Ready"
echo "=============================="
echo ""
echo "Open WebUI:"
echo "  http://localhost:3000"
echo "  https://cics.blaineai.me"
echo ""