#!/bin/bash

# Deployment script for Flight Logbook
# This script commits flight data changes and triggers GitHub Actions deployment

set -e  # Exit on error

echo "=========================================="
echo "Flight Logbook - Data Update & Deploy"
echo "=========================================="
echo ""

# Step 1: Export static site
echo "[1/2] Exporting static site..."
python manage.py export_static

if [ $? -ne 0 ]; then
    echo "ERROR: Static site export failed"
    exit 1
fi

echo ""

# Step 2: Commit and push changes
echo "[2/2] Committing and pushing changes..."

# Check if there are changes to commit
if git diff --quiet static_site/ && git diff --cached --quiet static_site/; then
    echo "No changes detected in static_site/. Nothing to commit."
else
    git add static_site/
    git commit -m "Update flight data - $(date '+%Y-%m-%d %H:%M:%S')"
    git push origin main

    echo ""
    echo "=========================================="
    echo "Deployment triggered!"
    echo "GitHub Actions will deploy your changes."
    echo "Check progress at:"
    echo "https://github.com/beirern/flight-logbook/actions"
    echo "=========================================="
fi
