#!/usr/bin/env bash

# Quick start script for Railway deployment

echo "=================================================="
echo "Railway Deployment - Quick Start"
echo "=================================================="
echo ""
echo "This script will guide you through deploying to Railway"
echo ""

# Step 1: Check git status
echo "Step 1: Checking git status..."
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
git status --short

echo ""
echo "Step 2: Stage deployment files..."
echo "Run these commands:"
echo ""
echo "  git add Procfile"
echo "  git add runtime.txt"
echo "  git add railway.json"
echo "  git add build.sh"
echo "  git add .env.example"
echo "  git add frontend/.env"
echo "  git add RAILWAY-DEPLOYMENT.md"
echo "  git add DEPLOYMENT-CHECKLIST.md"
echo "  git add RAILWAY-SETUP-SUMMARY.md"
echo "  git add verify-deployment.sh"
echo ""
echo "Or use: git add -A"
echo ""

echo "Step 3: Commit your changes..."
echo "  git commit -m 'chore: add Railway deployment configuration'"
echo ""

echo "Step 4: Push to GitHub..."
echo "  git push origin main"
echo ""

echo "Step 5: Visit https://railway.app..."
echo "  1. Sign in with GitHub"
echo "  2. Create new project"
echo "  3. Select 'Deploy from GitHub Repo'"
echo "  4. Choose this UrjaDrishti repository"
echo "  5. Select 'main' branch"
echo ""

echo "Step 6: Configure environment..."
echo "  In Railway Dashboard → Variables, add:"
echo "  API_KEY=your-secure-production-key"
echo ""

echo "Step 7: Enable auto-deploy..."
echo "  Settings → GitHub Integration → Enable Auto Deploy"
echo ""

echo "=================================================="
echo "For detailed instructions, see:"
echo "  - RAILWAY-DEPLOYMENT.md (Complete guide)"
echo "  - DEPLOYMENT-CHECKLIST.md (Verification steps)"
echo "  - RAILWAY-SETUP-SUMMARY.md (Quick reference)"
echo "=================================================="
