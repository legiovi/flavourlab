---
name: flavourlab
description: Aroma-based food pairing and recipe intelligence. Use when the user wants to find ingredient pairings, check whether ingredients work together, generate a new recipe, get a wine/beverage pairing, look up classical culinary base recipes (stocks, mother sauces, doughs, emulsions), or search 800+ real recipes. Built on flavour-pairing science (ingredients sharing volatile aroma compounds taste good together).
---

# FlavourLab

Aroma-based food pairing intelligence. Ingredients that share key aroma molecules
pair well together. This skill exposes a dependency-free CLI over a curated dataset
of **93 ingredients** (incl. wines & beverages), **17 aroma categories**,
**800+ real recipes** (full ingredients + methods), and **27 culinary foundations**.

## When to use
- "What goes with X?" / "What pairs with X?" → `pairings`
- "Do X, Y, Z work together?" → `harmony`
- "Invent / generate a recipe with X" → `generate`
- "What wine/drink with X?" → `drink`
- "Find real recipes using X" → `recipes`
- "How do I make béchamel / brown stock / pasta dough?" → `base` / `bases`
- "What ingredients are smoky / citrus / floral?" → `aroma`

## How to run
All commands print JSON. Run from this skill directory:

```bash
python3 flavourlab.py <command> [args]
```

### Commands

| Command | Example | Returns |
|---------|---------|---------|
| `pairings <id>` | `pairings strawberry --top 8` | best matches + shared aromas |
| `harmony <id...>` | `harmony strawberry basil tomato` | 0–100 harmony score + shared notes |
| `generate <base>` | `generate lamb --pair apricot --cuisine "Middle Eastern" --course main --method braised` | full recipe + science + drink + refs |
| `drink <id...>` | `drink beef black-pepper --type wine` | ranked wine/beverage pairings |
| `recipes <id...>` | `recipes tomato basil --cuisine Italian --limit 5` | real recipes w/ full method |
| `bases` | `bases --category "Mother Sauce"` | list culinary foundations |
| `base <id\|name>` | `base hollandaise` | full method for one foundation |
| `ingredients` | `ingredients --category wine` | list/search ingredients |
| `aroma <key>` | `aroma smoky` | all ingredients with that aroma |

### Ingredient IDs
Use lowercase kebab-case IDs (e.g. `cheese-blue`, `red-bell-pepper`, `black-pepper`,
`cabernet-sauvignon`, `sourdough-rye`). If unsure, run `ingredients --search <word>`
to find the id first.

### Aroma keys
`fruity, floral, citrus, green, woody, spicy, smoky, earthy, caramel, nutty, cheesy,
sulfurous, marine, minty, fermented, fatty, honey, tropical`

## Workflow guidance
1. If the user names an ingredient that isn't a known id, run `ingredients --search` first.
2. For "make me a recipe", call `generate`; then optionally `base <suggestedDrink/foundation>`
   and `recipes` to show real-world references.
3. Present results conversationally — translate the JSON into readable pairings,
   scores, and steps. Always explain *why* (the shared aroma compounds).
4. The harmony score: ≥70 excellent, 40–69 good, <40 adventurous/contrast.

## Notes
- All data is English and self-contained.
- The companion visual web app and MCP server live in the same repository
  (`public/` and `src/mcp-server.js`) if the user wants a GUI or persistent agent tools.
