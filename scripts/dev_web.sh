#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../apps/web"
npm run dev -- --host 127.0.0.1 --port 8022
