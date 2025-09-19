#!/bin/bash

# Simple Environment Switch Script
# Usage: ./switch-env.sh [local|staging|production]

ENV=${1:-local}

echo "🔄 Switching to $ENV environment..."

# Copy backend environment file
cp "backend/.env.$ENV" "backend/.env"

# Copy frontend environment file  
cp "frontend/.env.$ENV" "frontend/.env.local"

echo "✅ Switched to $ENV environment!"
echo "Backend: backend/.env"
echo "Frontend: frontend/.env.local"

# Show current branch strategy
echo ""
echo "📋 Branch Strategy:"
echo "  main branch     → Production (api.irisvision.ai)"
echo "  staging branch  → Staging (api-staging.irisvision.ai)"
echo "  local files    → Local development"
