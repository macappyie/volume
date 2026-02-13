#!/bin/bash

echo "🚀 Auto Git Push Started..."

git add .

# Agar koi change nahi hai toh exit
if git diff --cached --quiet; then
    echo "Nothing to commit. Working tree clean."
    exit 0
fi

msg="auto update $(date '+%Y-%m-%d %H:%M:%S')"

git commit -m "$msg"
git push origin main

echo "✅ Done"

