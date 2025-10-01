#!/bin/bash

# Quick Deploy Script for Railway
# This script prepares your MCP server for Railway deployment

set -e

echo "🚂 Railway Deployment Setup"
echo "=========================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed"
    exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Create project directory
PROJECT_DIR="$HOME/fal-image-mcp-server-railway"
echo "📁 Creating project at: $PROJECT_DIR"

if [ -d "$PROJECT_DIR" ]; then
    echo "⚠️  Directory exists. Overwrite? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled"
        exit 0
    fi
    rm -rf "$PROJECT_DIR"
fi

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "✅ Directory created"
echo ""

# Get credentials
echo "🔑 API Credentials"
echo ""
echo "Enter your fal.ai API Key:"
read -r FAL_API_KEY
echo ""
echo "Enter your Slack Bot Token:"
read -r SLACK_BOT_TOKEN
echo ""

# Create package.json
echo "📦 Creating package.json..."
cat > package.json << 'EOF'
{
  "name": "fal-image-modifier-mcp-server",
  "version": "1.0.0",
  "description": "MCP HTTP Server for fal.ai image modification with Slack integration",
  "type": "module",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "dev": "node --watch index.js"
  },
  "keywords": [
    "mcp",
    "fal.ai",
    "image-modification",
    "slack",
    "runbear",
    "railway"
  ],
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0",
    "node-fetch": "^3.3.2",
    "express": "^4.18.2",
    "cors": "^2.8.5"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
node_modules/
.env
*.log
.DS_Store
EOF

# Create railway.json
cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "node index.js",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
EOF

# Create .env.example
cat > .env.example << 'EOF'
FAL_API_KEY=your_fal_api_key_here
SLACK_BOT_TOKEN=xoxb-your-slack-token-here
PORT=3000
EOF

# Create README
cat > README.md << 'EOF'
# fal.ai Image Modifier MCP Server

MCP server for AI-powered image modification with Slack integration.

## Features

- 🎨 AI image modification using fal.ai
- 📤 Direct Slack integration
- 🔄 Complete workflows (modify + send)
- 🌐 HTTP/SSE transport for web compatibility

## Deployment

This server is designed to run on Railway.app

### Environment Variables

Set these in Railway:
- `FAL_API_KEY` - Your fal.ai API key
- `SLACK_BOT_TOKEN` - Your Slack bot token
- `PORT` - Server port (Railway sets this automatically)

## Tools

- `modify_image` - Modify images with AI
- `send_to_slack` - Send images to Slack
- `modify_and_send_to_slack` - Complete workflow

## Usage

Connect to this server in Runbear using the SSE endpoint:
`https://your-app.railway.app/sse`
EOF

echo "✅ Project files created"
echo ""

# Create .env for local testing
cat > .env << EOF
FAL_API_KEY=$FAL_API_KEY
SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN
PORT=3000
EOF

echo "⚠️  IMPORTANT: You need to manually create index.js"
echo ""
echo "Copy the HTTP Server code from the artifact and save it as:"
echo "   $PROJECT_DIR/index.js"
echo ""
echo "Press Enter when you've created index.js..."
read -r

if [ ! -f "index.js" ]; then
    echo "❌ index.js not found"
    exit 1
fi

chmod +x index.js

# Install dependencies
echo "📥 Installing dependencies..."
npm install
echo ""

# Initialize git
echo "📝 Initializing git repository..."
git init
git add .
git commit -m "Initial commit: MCP server for fal.ai image modification"
echo ""

# Test locally (optional)
echo "🧪 Would you like to test locally first? (y/n)"
read -r test_response

if [[ "$test_response" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting server on http://localhost:3000"
    echo "Press Ctrl+C to stop"
    echo ""
    export $(cat .env | xargs)
    npm start
fi

echo ""
echo "=========================="
echo "✅ Setup Complete!"
echo "=========================="
echo ""
echo "📍 Project location: $PROJECT_DIR"
echo ""
echo "🚂 Next Steps for Railway Deployment:"
echo ""
echo "1. Create a GitHub repository:"
echo "   gh repo create fal-image-mcp-server --public --source=. --remote=origin"
echo "   git push -u origin main"
echo ""
echo "2. Go to https://railway.app"
echo "3. Sign in with GitHub"
echo "4. Click 'New Project' → 'Deploy from GitHub'"
echo "5. Select your repository"
echo ""
echo "6. Add environment variables in Railway:"
echo "   FAL_API_KEY=$FAL_API_KEY"
echo "   SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN"
echo ""
echo "7. Railway will deploy automatically!"
echo ""
echo "8. Get your URL from Railway dashboard"
echo "   MCP endpoint will be: https://your-app.railway.app/sse"
echo ""
echo "9. Add to Runbear:"
echo "   - Name: fal-image-modifier"
echo "   - URL: https://your-app.railway.app/sse"
echo ""
echo "🎉 Happy deploying!"