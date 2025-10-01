# fal.ai Image Modifier MCP Server

MCP HTTP server exposing AI image modification via fal.ai, with optional Slack posting. Deployable to Railway and consumable by Runbear as a custom MCP server.

## Quick Start

1) Install

```bash
npm install
```

2) Set environment variables (create a local .env):

- `FAL_API_KEY`: fal.ai API key
- `SLACK_BOT_TOKEN`: Slack bot token
- `PORT`: optional; defaults to 3000

3) Run locally

```bash
# PowerShell example
$env:FAL_API_KEY="..."; $env:SLACK_BOT_TOKEN="..."; $env:PORT="3000"; npm start
```

Health: `http://localhost:3000/health`
MCP SSE: `http://localhost:3000/sse`

## Tools

- `modify_image`: Modify an image using a text prompt; returns a URL.
- `send_to_slack`: Post an image URL to a Slack channel.
- `modify_and_send_to_slack`: Modify then post to Slack.

## Deploy to Railway

- Commit and push this repo to GitHub.
- On Railway: New Project → Deploy from GitHub → select repo.
- Add variables: `FAL_API_KEY`, `SLACK_BOT_TOKEN` (Railway injects `PORT`).
- After deploy, your MCP endpoint is: `https://<your-app>.railway.app/sse`.

## Use in Runbear

- Add a custom MCP server in Runbear:
  - Name: `fal-image-modifier`
  - URL: `https://<your-app>.railway.app/sse`

## Slack Setup

- Create a Slack app with a Bot Token (`xoxb-...`).
- Scopes needed: `chat:write`, plus any channel read scopes required by your workspace policy.
- Invite the bot to your target channel.

## Notes

- Requires Node 18+.
- Set `FAL_API_KEY` and `SLACK_BOT_TOKEN` for production.
