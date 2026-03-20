# Deploy Todoist MCP Server — Claude Code Prompt

Paste this into Claude Code from your `~/Projects` directory after copying the `todoist-mcp` folder there.

---

```
I need you to deploy the todoist-mcp project in ~/Projects/todoist-mcp to my Hetzner VPS via Coolify.

## Context

This is a Python MCP server (FastMCP) that connects Claude Desktop and Claude Code to my Todoist account. It's a lightweight single-container app (Flavor A from my infra standards, but using GHCR image builds like Flavor B to avoid source-building on the VPS).

Read the infra-standards skill FIRST for my deployment patterns, then consult Infra Brain (the app-brain MCP) for any version pins or lessons learned.

## What's already done

- All source code is complete and tested (src/server.py, src/client.py)
- Dockerfile exists and is ready
- GitHub Actions workflow exists at .github/workflows/deploy.yml
- README.md has full docs

## What you need to do

### 1. GitHub repo setup
- Create a new GitHub repo: `alobarquest/todoist-mcp` (private)
- Initialize git in ~/Projects/todoist-mcp if not already
- Add remote, commit all files, push to main
- Confirm the GitHub Actions workflow runs and the GHCR image builds successfully
- Make sure the GHCR package is accessible to Coolify (may need to set package visibility or use a PAT)

### 2. Coolify resource setup
- Use the Coolify API (check infra-brain or my env for COOLIFY_API_TOKEN and the Coolify base URL) to create a new resource:
  - **Type:** Docker Image
  - **Image:** ghcr.io/alobarquest/todoist-mcp:latest
  - **Port:** 8000
  - **Domain:** todoist-mcp.devonwatkins.com
  - **Health check:** GET http://127.0.0.1:8000/mcp
- If the Coolify API is too complex for this, give me the exact manual steps in the Coolify UI instead

### 3. Secrets wiring
- The app needs one secret: TODOIST_API_TOKEN
- Check BWS for an existing Todoist token. If none exists, remind me to create one at: Todoist → Settings → Integrations → Developer, then store it in BWS
- Wire the BWS secret into Coolify as an environment variable
- Also add GitHub repo secrets: COOLIFY_WEBHOOK_URL and COOLIFY_API_TOKEN (get the webhook URL from the Coolify resource you just created)

### 4. DNS
- Remind me to create a DNS A record or CNAME for todoist-mcp.devonwatkins.com pointing to the VPS IP (or confirm it's already wildcarded)

### 5. Verification
- After deployment, confirm:
  - The GHCR image exists and is tagged
  - The Coolify resource is running
  - https://todoist-mcp.devonwatkins.com/mcp responds
  - Health check passes

### 6. Register with App Brain
- Use the app-brain MCP (capture_knowledge or onboard_app) to register todoist-mcp:
  - slug: todoist-mcp
  - name: Todoist MCP Server
  - status: active
  - description: MCP server exposing Todoist REST API v2 as 24 tools (tasks, projects, sections, comments, labels CRUD) for Claude Desktop, Cowork, and Claude Code. Runs as a single Docker container with streamable HTTP transport.
  - tags: mcp, todoist, python, fastmcp, docker, coolify
  - tech_stack: {"language": "python", "framework": "fastmcp", "transport": "streamable_http", "database": "none"}
  - repo_path: github.com/alobarquest/todoist-mcp
  - deployment_url: https://todoist-mcp.devonwatkins.com

### 7. Claude Desktop + Claude Code config
- Show me the exact JSON snippets to add to:
  - Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json)
  - Claude Code config (~/.claude/settings.json)
- Both should point to the remote URL: https://todoist-mcp.devonwatkins.com/mcp/

## Important rules
- NEVER source-build on the VPS — always GHCR image pull
- All secrets via BWS → Coolify env vars, never hardcoded
- Follow my infra-standards skill for all patterns
- If you hit a blocker, tell me what manual step I need to do rather than guessing
```
