# Push FlavourLab to GitHub

1. Go to https://github.com/new and create a repo named `flavourlab` (public)
2. Then run these commands:

```bash
cd /Users/usuario/foodpairing-lab
git remote add origin https://github.com/YOUR_USERNAME/flavourlab.git
git push -u origin main
```

3. Enable GitHub Pages: Settings → Pages → Source: GitHub Actions
   → The workflow in `.github/workflows/pages.yml` auto-deploys `public/` on every push.

4. Your live app URL will be: https://YOUR_USERNAME.github.io/flavourlab

## To add to Claude Code as MCP server (after push):

In ~/.claude/settings.json:
```json
{
  "mcpServers": {
    "flavourlab": {
      "command": "node",
      "args": ["/Users/usuario/foodpairing-lab/src/mcp-server.js"]
    }
  }
}
```
