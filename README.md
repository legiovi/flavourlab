# FlavourLab 🧪

**Aroma-based food pairing intelligence — visual app + MCP server for AI agents**

A science-based tool for discovering ingredient pairings and generating recipes based on shared volatile organic compounds (aroma molecules). Includes:

- 🕸 **Interactive flavour network** — D3.js force graph of 60+ ingredients connected by aroma links
- 🎨 **Pairing builder** — build ingredient combinations and score their aromatic harmony
- ✨ **Recipe generator** — generate complete recipes using flavour pairing science + 540 real recipes
- 🌸 **Aroma explorer** — browse 17 aroma note categories and the ingredients that share them
- 🤖 **MCP server** — 7 tools for AI agents to query pairing data and generate recipes

---

## Quick Start — Visual App

```bash
git clone https://github.com/YOUR_USERNAME/flavourlab
cd flavourlab
npm run serve
# Open http://localhost:8765
```

No build step. Pure HTML/JS with D3.js loaded from CDN.

---

## MCP Server (for AI agents)

### Install via npm

```bash
npm install -g flavourlab
```

### Or run directly with npx

```bash
npx flavourlab
```

### Add to Claude Code / Claude Desktop

In your `claude_desktop_config.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "flavourlab": {
      "command": "npx",
      "args": ["flavourlab"]
    }
  }
}
```

Or if cloned locally:

```json
{
  "mcpServers": {
    "flavourlab": {
      "command": "node",
      "args": ["/path/to/flavourlab/src/mcp-server.js"]
    }
  }
}
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_ingredient` | Full ingredient details: aroma profile, pairings, description |
| `list_ingredients` | All 60+ ingredients, filterable by category or search |
| `get_pairings` | Best matches for an ingredient ranked by shared aroma compounds |
| `check_harmony` | Aromatic harmony score (0–100) for a set of ingredients |
| `generate_recipe` | Full recipe with ingredients, method, aroma science, real-world references |
| `find_recipes` | Search 540 real recipes by ingredient and cuisine |
| `get_aroma_ingredients` | All ingredients sharing a specific aroma note |

### Example agent usage

```
User: What pairs well with strawberry?
Agent: [calls get_pairings("strawberry")]
→ Returns: chocolate, basil, tomato, vanilla, citrus... with shared aroma explanations

User: Score the harmony of strawberry + basil + tomato
Agent: [calls check_harmony(["strawberry", "basil", "tomato"])]
→ Returns: score 78/100, shared notes: Fruity×3, Floral×2, Citrus×2

User: Generate a Spanish starter recipe using strawberry and basil
Agent: [calls generate_recipe({base:"strawberry", pair:"basil", cuisine:"Spanish", course:"starter"})]
→ Returns: full recipe with science explanation and real recipe references
```

---

## Data

- **60+ ingredients** across 8 categories (fruit, vegetable, herb, spice, protein, dairy, beverage, other)
- **17 aroma note categories** derived from volatile organic compound analysis
- **540 real recipes** extracted from culinary sources across Italian, Mexican, Middle Eastern, Nordic, Catalan, Spanish Avant-Garde, and Baking traditions
- Pairing data sourced from published flavour pairing research

---

## Structure

```
flavourlab/
├── public/
│   ├── index.html          # Single-file visual app
│   ├── data.js             # Ingredient + aroma database
│   └── recipes_final.json  # 540 extracted real recipes
├── src/
│   └── mcp-server.js       # MCP server (7 tools)
├── data/
│   ├── data.js
│   └── recipes_final.json
└── package.json
```

---

## License

MIT
