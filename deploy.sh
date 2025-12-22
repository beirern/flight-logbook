#!/bin/bash

# Deployment script for Flight Logbook static site to GitHub Pages
# This script exports the static site and deploys it to GitHub

set -e  # Exit on error

echo "=========================================="
echo "Flight Logbook - GitHub Pages Deployment"
echo "=========================================="
echo ""

# Step 1: Export static site
echo "[1/3] Exporting static site..."
python manage.py export_static

if [ $? -ne 0 ]; then
    echo "ERROR: Static site export failed"
    exit 1
fi

echo ""

# Step 2: Commit changes
echo "[2/3] Committing changes to git..."

# Check if there are changes to commit
if git diff --quiet static_site/ && git diff --cached --quiet static_site/; then
    echo "No changes detected in static_site/. Nothing to commit."
else
    git add static_site/
    git commit -m "Update flight data - $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo ""

# Step 3: Push to GitHub
echo "[3/3] Pushing to GitHub..."
git push origin main

if [ $? -ne 0 ]; then
    echo "ERROR: Git push failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "Your site will update in ~1 minute."
echo "=========================================="
