#!/usr/bin/env bash
# =========================================================
# Açar🔐 — Push to GitHub (run this ON YOUR SERVER or PC)
# =========================================================
# Usage:
#   GITHUB_USER=yourusername GITHUB_REPO=acar-panel GITHUB_TOKEN=ghp_xxx ./scripts/push-to-github.sh
#
# Or manually:
#   git remote add origin https://github.com/YOUR_USER/REPO.git
#   git push -u origin master
# =========================================================

set -e

USER="${GITHUB_USER:-}"
REPO="${GITHUB_REPO:-acar-panel}"
TOKEN="${GITHUB_TOKEN:-}"
BRANCH="${GITHUB_BRANCH:-master}"

if [ -z "$USER" ]; then
    echo "❌ Set GITHUB_USER=your_github_username"
    exit 1
fi

if [ -z "$TOKEN" ]; then
    echo "❌ Set GITHUB_TOKEN=ghp_xxxxxxxx (your personal access token with 'repo' scope)"
    echo "   Create one: https://github.com/settings/tokens/new"
    exit 1
fi

REMOTE_URL="https://${TOKEN}@github.com/${USER}/${REPO}.git"

echo "🔗 Setting remote origin..."
if git remote get-url origin &>/dev/null; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

echo "🚀 Pushing to github.com/${USER}/${REPO}..."
git push -u origin "$BRANCH"

echo ""
echo "✅ Pushed to https://github.com/${USER}/${REPO}"
