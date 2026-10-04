#!/usr/bin/env bash
# Run on the authorized RunPod only. No browser or runtime is installed locally.
set -euo pipefail
cd /workspace/palimpsest
mkdir -p .tools/downloads .tools/browser
curl -fsSL https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt -o .tools/downloads/node-shasums.txt
node_archive=$(awk '/ node-v24\.[0-9]+\.[0-9]+-linux-x64.tar.xz$/ {print $2}' .tools/downloads/node-shasums.txt)
test -n "$node_archive"
test "$(printf '%s\n' "$node_archive" | wc -l)" -eq 1
curl -fsSL "https://nodejs.org/dist/latest-v24.x/$node_archive" -o ".tools/downloads/$node_archive"
awk -v file="$node_archive" '$2 == file {print}' .tools/downloads/node-shasums.txt > .tools/downloads/node-selected.sha256
(cd .tools/downloads && sha256sum -c node-selected.sha256)
mkdir -p .tools/node
tar -xJf ".tools/downloads/$node_archive" -C .tools/node --strip-components=1
export PATH="$PWD/.tools/node/bin:$PATH"
node --version
npm --version
npm install --prefix .tools/browser --no-audit --no-fund @playwright/cli playwright
.tools/browser/node_modules/.bin/playwright install --with-deps chromium
.tools/browser/node_modules/.bin/playwright-cli --help
rm -- ".tools/downloads/$node_archive"
