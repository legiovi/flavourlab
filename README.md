# FlavourLab 🧪

**Aroma-based food pairing intelligence — visual app + MCP server for AI agents**

A science-based tool for discovering ingredient pairings and generating recipes based on shared volatile organic compounds (aroma molecules). Includes:

- 🕸 **Interactive flavour network** — D3.js force graph of ingredients connected by aroma links
- 🎨 **Pairing builder** — build ingredient combinations and score their aromatic harmony
- ✨ **Recipe generator** — generate complete recipes using flavour pairing science + 800+ real recipes
- 🌸 **Aroma explorer** — browse 17 aroma note categories and the ingredients that share them
- 📖 **Culinary foundations** — 27 classical base recipes & techniques (stocks, mother sauces, doughs, emulsions)
- 🤖 **MCP server** — 9 tools for AI agents to query pairing data, browse foundations, and generate recipes

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
| `find_recipes` | Search 800+ real recipes (full ingredients + method) by ingredient and cuisine |
| `get_aroma_ingredients` | All ingredients sharing a specific aroma note |
| `list_culinary_bases` | List the 27 foundational base recipes & techniques |
| `get_culinary_base` | Full method for a base (béchamel, brown stock, pasta dough, mayonnaise…) |

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

- **Ingredients** across 8 categories (fruit, vegetable, herb, spice, protein, dairy, beverage, other)
- **17 aroma note categories** derived from volatile organic compound analysis
- **800+ real recipes** (with full ingredients & methods) across Italian, Middle Eastern, Mexican, Baking, Catalan, Spanish, Nordic, American, Cambodian, Asian, Seafood, French and more
- **27 culinary foundations** — stocks, the five mother sauces, doughs, emulsions, pastry bases and core techniques
- All recipe text is English-only and self-contained (no external attribution)
- Pairing data based on shared volatile aroma compounds (flavour pairing science)

---

## Structure

```
flavourlab/
├── public/                   # Visual web app (deployable as static site)
│   ├── index.html            # Single-file visual app (5 views)
│   ├── data.js               # Ingredient + aroma database
│   ├── recipes.json          # 800+ extracted real recipes
│   └── culinary_bases.json   # 27 culinary foundations
├── src/
│   └── mcp-server.js         # MCP server (9 tools)
├── data/                     # Source datasets (mirrored to public)
│   ├── data.js
│   ├── recipes.json
│   └── culinary_bases.json
├── tools/                    # Dataset build pipeline
│   ├── extract_epubs.py      # Generic EPUB recipe extractor (English-only)
│   └── build_dataset.py      # Merge + clean + ingredient-link
└── package.json
```

---

## License

MIT
