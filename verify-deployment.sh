#!/usr/bin/env bash

# Railway Deployment Verification Script
set -e

echo "=================================================="
echo "Railway Deployment Verification"
echo "=================================================="
echo ""

ERRORS=0

check_file() {
  if [ -f "$1" ]; then
    echo "✓ $1"
  else
    echo "✗ MISSING: $1"
    ERRORS=$((ERRORS + 1))
  fi
}

check_dir() {
  if [ -d "$1" ]; then
    echo "✓ $1/"
  else
    echo "✗ MISSING: $1/"
    ERRORS=$((ERRORS + 1))
  fi
}

echo "Checking deployment files..."
check_file "Procfile"
check_file "runtime.txt"
check_file "railway.json"
check_file "build.sh"
check_file ".env.example"
check_file "RAILWAY-DEPLOYMENT.md"
echo ""

echo "Checking project structure..."
check_dir "backend"
check_dir "frontend"
check_dir "data"
echo ""

echo "Checking backend..."
check_file "backend/requirements.txt"
check_file "backend/src/main.py"
check_file "backend/src/auth.py"
echo ""

echo "Checking frontend..."
check_file "frontend/package.json"
check_file "frontend/src/App.jsx"
check_file "frontend/.env"
echo ""

if [ $ERRORS -eq 0 ]; then
  echo "=================================================="
  echo "✓ All checks passed! Ready for Railway deployment"
  echo "=================================================="
  echo ""
  echo "Next steps:"
  echo "1. Ensure all changes are committed to git"
  echo "2. Push to GitHub: git push origin main"
  echo "3. Visit https://railway.app and create a new project"
  echo "4. Connect your GitHub repository"
  echo "5. Set environment variables in Railway dashboard"
  echo "6. Enable auto-deploy"
  echo ""
  exit 0
else
  echo "=================================================="
  echo "✗ $ERRORS error(s) found. Please fix and try again."
  echo "=================================================="
  exit 1
fi
