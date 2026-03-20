# Todoist MCP Server

MCP server that connects Claude Desktop, Cowork, and Claude Code to your Todoist account. Full CRUD for tasks, projects, sections, comments, and labels.

## Tools (25 total)

### Tasks
- `todoist_list_tasks` — List/filter tasks (by project, section, label, or Todoist filter syntax)
- `todoist_get_task` — Get a single task by ID
- `todoist_create_task` — Create with due dates, priority, labels, recurring schedules
- `todoist_update_task` — Update any task field
- `todoist_close_task` — Mark complete (advances recurring tasks)
- `todoist_reopen_task` — Reopen a completed task
- `todoist_delete_task` — Permanently delete

### Projects
- `todoist_list_projects` / `todoist_get_project` / `todoist_create_project` / `todoist_update_project` / `todoist_delete_project`

### Sections
- `todoist_list_sections` / `todoist_create_section` / `todoist_update_section` / `todoist_delete_section`

### Comments
- `todoist_list_comments` / `todoist_create_comment` / `todoist_update_comment` / `todoist_delete_comment`

### Labels
- `todoist_list_labels` / `todoist_create_label` / `todoist_update_label` / `todoist_delete_label`

## Prerequisites

1. **Todoist API Token** — Get from: Todoist → Settings → Integrations → Developer
2. **Python 3.12+** (for local use) or **Docker** (for VPS deployment)

## Quick Start — Local (stdio)

```bash
# Clone and install
git clone https://github.com/alobarquest/todoist-mcp.git
cd todoist-mcp
pip install -r requirements.txt

# Set your token
export TODOIST_API_TOKEN="your_token_here"

# Run (stdio mode for local clients)
python -m src.server
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/todoist-mcp",
      "env": {
        "TODOIST_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Claude Code Configuration

Add to your project's `.mcp.json` or global `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/todoist-mcp",
      "env": {
        "TODOIST_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Remote Server (VPS via Coolify)

When deployed to the VPS, the server runs in streamable HTTP mode.

### Connect Claude Desktop to the remote server:

```json
{
  "mcpServers": {
    "todoist": {
      "url": "https://todoist-mcp.devonwatkins.com/mcp/"
    }
  }
}
```

### Environment variables for Coolify:

| Variable | Description |
|---|---|
| `TODOIST_API_TOKEN` | Your Todoist API token (from BWS) |
| `MCP_TRANSPORT` | `streamable_http` (set in Dockerfile) |
| `MCP_PORT` | `8000` (set in Dockerfile) |

## Deployment — Coolify/Hetzner VPS

This follows **Flavor A** from Devon's Infra Standards (lightweight, single container).

However, since we use GHCR image pulls (not source build), the CI/CD follows the Flavor B pattern:

1. Push to `main` → GitHub Actions builds image → pushes to `ghcr.io/alobarquest/todoist-mcp`
2. Coolify webhook triggers redeploy → pulls latest image

### Coolify Setup

- **Build type:** Docker Image
- **Image:** `ghcr.io/alobarquest/todoist-mcp:latest`
- **Port:** 8000
- **Domain:** `todoist-mcp.devonwatkins.com`
- **Health check:** `http://127.0.0.1:8000/mcp`
- **Environment:** `TODOIST_API_TOKEN` from BWS

### GitHub Repo Secrets

- `COOLIFY_WEBHOOK_URL` — Coolify deploy webhook for this resource
- `COOLIFY_API_TOKEN` — Coolify API bearer token

## Rate Limits

Todoist allows **1000 requests per user per 15 minutes**. The server returns a clear error message if you hit this limit.

## License

MIT
