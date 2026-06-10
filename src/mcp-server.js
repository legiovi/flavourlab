#!/usr/bin/env node
/**
 * FlavourLab MCP Server
 * Exposes aroma-based food pairing intelligence as MCP tools for AI agents.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ─── Load data ───────────────────────────────────────────────────────────────
const dataPath = join(__dirname, "../data");

// Inline the ingredients data (parsed from data.js)
const dataJs = readFileSync(join(dataPath, "data.js"), "utf-8");
// Extract INGREDIENTS array via regex-free eval in Node context
let INGREDIENTS, AROMA_NOTES, CATEGORY_COLORS, CATEGORY_LABELS, SWAP_FAMILY;
const evalScope = {};
new Function(
  "module", "exports",
  dataJs + "\nmodule.INGREDIENTS=INGREDIENTS;module.AROMA_NOTES=AROMA_NOTES;module.CATEGORY_COLORS=CATEGORY_COLORS;module.CATEGORY_LABELS=CATEGORY_LABELS;module.SWAP_FAMILY=typeof SWAP_FAMILY!=='undefined'?SWAP_FAMILY:{};"
)(evalScope, {});
INGREDIENTS = evalScope.INGREDIENTS;
AROMA_NOTES = evalScope.AROMA_NOTES;
CATEGORY_COLORS = evalScope.CATEGORY_COLORS;
CATEGORY_LABELS = evalScope.CATEGORY_LABELS;
SWAP_FAMILY = evalScope.SWAP_FAMILY || {};

function familyOf(id) {
  for (const k in SWAP_FAMILY) if (SWAP_FAMILY[k].includes(id)) return k;
  return null;
}
function getVariations(id, n = 6) {
  const ing = ingMap[id];
  if (!ing) return [];
  const fam = familyOf(id);
  return INGREDIENTS.filter(o => o.id !== id && (fam ? familyOf(o.id) === fam : o.category === ing.category))
    .map(o => {
      const shared = ing.aromas.filter(a => o.aromas.includes(a));
      return { id: o.id, name: o.name, category: o.category, sharedAromas: shared.map(a => AROMA_NOTES[a]?.label || a), score: shared.length };
    })
    .sort((a, b) => b.score - a.score).slice(0, n);
}

const RECIPES = JSON.parse(readFileSync(join(dataPath, "recipes.json"), "utf-8"));
const BASES = JSON.parse(readFileSync(join(dataPath, "culinary_bases.json"), "utf-8"));
let BOOK_PAIRINGS = {};
try { BOOK_PAIRINGS = JSON.parse(readFileSync(join(dataPath, "book_pairings.json"), "utf-8")); } catch {}
const ingMap = Object.fromEntries(INGREDIENTS.map(i => [i.id, i]));

// ─── Helpers ─────────────────────────────────────────────────────────────────
function buildPairingGraph() {
  const conns = [];
  for (let i = 0; i < INGREDIENTS.length; i++) {
    for (let j = i + 1; j < INGREDIENTS.length; j++) {
      const a = INGREDIENTS[i], b = INGREDIENTS[j];
      const shared = a.aromas.filter(ar => b.aromas.includes(ar));
      if (shared.length >= 2 || a.pairings.includes(b.id) || b.pairings.includes(a.id)) {
        conns.push({ source: a.id, target: b.id, sharedAromas: shared, strength: shared.length });
      }
    }
  }
  return conns;
}
const pairGraph = buildPairingGraph();

function getPairings(ingredientId, topN = 10) {
  const ing = ingMap[ingredientId];
  if (!ing) return [];
  return pairGraph
    .filter(c => c.source === ingredientId || c.target === ingredientId)
    .map(c => {
      const otherId = c.source === ingredientId ? c.target : c.source;
      const other = ingMap[otherId];
      return {
        id: other.id,
        name: other.name,
        emoji: other.emoji,
        category: other.category,
        sharedAromas: c.sharedAromas,
        strength: c.strength,
        isVerifiedPairing: ing.pairings.includes(other.id) || other.pairings.includes(ing.id),
      };
    })
    .filter(x => x)
    .sort((a, b) => b.strength - a.strength || (b.isVerifiedPairing ? 1 : 0))
    .slice(0, topN);
}

function scoreHarmony(ingredientIds) {
  let total = 0, max = 0;
  const freq = {};
  for (const id of ingredientIds) {
    const ing = ingMap[id];
    if (!ing) continue;
    ing.aromas.forEach(a => { freq[a] = (freq[a] || 0) + 1; });
  }
  for (let i = 0; i < ingredientIds.length; i++) {
    for (let j = i + 1; j < ingredientIds.length; j++) {
      const a = ingMap[ingredientIds[i]], b = ingMap[ingredientIds[j]];
      if (!a || !b) continue;
      const shared = a.aromas.filter(ar => b.aromas.includes(ar));
      total += shared.length;
      max += Math.max(a.aromas.length, b.aromas.length);
    }
  }
  return {
    score: max > 0 ? Math.min(100, Math.round((total / max) * 320)) : 0,
    sharedAromas: Object.entries(freq).filter(([, c]) => c >= 2).sort((a, b) => b[1] - a[1]),
  };
}

const SWEET_ONLY = new Set(["chocolate", "vanilla"]);
const SUPPORT_BONUS = { herb: 3, spice: 3, other: 2, vegetable: 2, dairy: 1, fruit: 1 };
function pickFillers(core, count, course) {
  if (count <= 0) return [];
  const coreIds = new Set(core.map(i => i.id));
  const proteinsInCore = core.filter(i => i.category === "protein").length;
  const isDessert = course === "dessert", isDrink = course === "cocktail";
  const need = Math.ceil(core.length / 2);
  return INGREDIENTS.filter(o => !coreIds.has(o.id)).map(o => {
    let pairCount = 0, aromaTotal = 0, verified = 0;
    core.forEach(c => {
      const sh = c.aromas.filter(a => o.aromas.includes(a));
      aromaTotal += sh.length;
      const isPair = c.pairings.includes(o.id) || o.pairings.includes(c.id);
      if (sh.length > 0 || isPair) pairCount++;
      if (isPair) verified++;
    });
    return { ing: o, pairCount, score: aromaTotal + verified * 3 + (SUPPORT_BONUS[o.category] || 0) };
  })
    .filter(x => x.pairCount >= need)
    .filter(x => !(proteinsInCore >= 1 && x.ing.category === "protein"))
    .filter(x => x.ing.category !== "wine" && x.ing.category !== "beverage")
    .filter(x => isDessert || isDrink ? true : !SWEET_ONLY.has(x.ing.id))
    .sort((a, b) => b.pairCount - a.pairCount || b.score - a.score)
    .slice(0, count).map(x => x.ing);
}

function generateRecipe({ baseId, pairId, cuisine = "any", course = "any", method = "any", complexity = "medium", extraIds = [] }) {
  const base = ingMap[baseId];
  if (!base) throw new Error(`Unknown ingredient: ${baseId}`);
  const pair = pairId ? ingMap[pairId] : null;
  const extra = extraIds.map(id => ingMap[id]).filter(Boolean);

  const ingCount = complexity === "simple" ? 5 : complexity === "complex" ? 10 : 7;
  const selected = [base];
  if (pair) selected.push(pair);
  extra.forEach(e => selected.push(e));
  pickFillers(selected, ingCount - selected.length, course).forEach(f => selected.push(f));

  const aromaFreq = {};
  selected.forEach(i => i.aromas.forEach(a => { aromaFreq[a] = (aromaFreq[a] || 0) + 1; }));
  const topAromas = Object.entries(aromaFreq).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([a]) => a);

  const sharedWithPair = pair ? base.aromas.filter(a => pair.aromas.includes(a)) : [];
  const harmony = scoreHarmony(selected.map(i => i.id));

  const matchingRecipes = RECIPES.filter(r => {
    const rl = r.linked_ingredients || [];
    const ids = selected.map(i => i.id);
    const overlap = ids.filter(id => rl.includes(id)).length;
    const cuMatch = cuisine === "any" || r.cuisine.toLowerCase().includes(cuisine.toLowerCase());
    return overlap >= 1 && cuMatch;
  }).sort((a, b) => {
    const ids = selected.map(i => i.id);
    return (b.linked_ingredients || []).filter(id => ids.includes(id)).length
         - (a.linked_ingredients || []).filter(id => ids.includes(id)).length;
  }).slice(0, 5);

  return {
    name: buildName(base, pair, cuisine, course, method),
    cuisine: cuisine === "any" ? "Modern" : cuisine,
    course: course === "any" ? "Main" : course,
    method: method === "any" ? "Prepared" : method,
    complexity,
    servings: course === "cocktail" ? "2 glasses" : course === "snack" ? "12 pieces" : "4 servings",
    ingredients: selected.map((ing, idx) => ({
      id: ing.id,
      name: ing.name,
      emoji: ing.emoji,
      quantity: getQty(ing, idx),
      role: idx === 0 ? "base" : idx === 1 && pair ? "pairing" : "supporting",
    })),
    aromaProfile: topAromas.map(a => ({
      key: a,
      label: AROMA_NOTES[a]?.label || a,
      icon: AROMA_NOTES[a]?.icon || "",
    })),
    pairingScience: pair ? {
      sharedAromas: sharedWithPair,
      overlapScore: Math.round(sharedWithPair.length / Math.max(base.aromas.length, pair.aromas.length) * 100),
      explanation: `${base.name} and ${pair.name} share ${sharedWithPair.length} key aroma molecule(s): ${sharedWithPair.map(a => AROMA_NOTES[a]?.label || a).join(", ")}.`,
    } : null,
    harmonyScore: harmony.score,
    referenceRecipes: matchingRecipes.map(r => ({ name: r.name, cuisine: r.cuisine, source: r.source })),
  };
}

function buildName(base, pair, cuisine, course, method) {
  const ma = { roasted: "Roasted", grilled: "Grilled", sautéed: "Sautéed", braised: "Braised", raw: "Raw", emulsified: "Emulsified", fermented: "Cured", any: "" };
  const m = ma[method] || "";
  if (course === "cocktail") return `${base.name}${pair ? ` & ${pair.name}` : ""} Cocktail`;
  if (course === "dessert") return `${m} ${base.name}${pair ? ` with ${pair.name}` : ""} Dessert`.trim();
  if (!pair) return `${m} ${base.name}`.trim();
  return `${m} ${base.name} with ${pair.name}`.trim();
}

function getQty(ing, idx) {
  const Q = { protein: ["200g","150g","180g"], dairy: ["80g","60g"], fruit: ["2","1"], vegetable: ["150g","100g"], herb: ["handful","2 tbsp"], spice: ["1 tsp","½ tsp"], beverage: ["60ml","30ml"], other: ["2 tbsp","1 tbsp"] };
  const arr = Q[ing.category] || ["to taste"];
  return arr[idx % arr.length];
}

// ─── MCP Server ──────────────────────────────────────────────────────────────
const server = new Server(
  { name: "flavourlab", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "get_ingredient",
      description: "Get full details about an ingredient including its aroma profile, classic pairings, and category.",
      inputSchema: {
        type: "object",
        properties: {
          id: { type: "string", description: "Ingredient ID (e.g. 'chocolate', 'strawberry', 'basil')" },
        },
        required: ["id"],
      },
    },
    {
      name: "list_ingredients",
      description: "List all available ingredients, optionally filtered by category.",
      inputSchema: {
        type: "object",
        properties: {
          category: { type: "string", description: "Filter by category: fruit, vegetable, herb, spice, protein, dairy, beverage, other" },
          search: { type: "string", description: "Search term to filter by name or aroma" },
        },
      },
    },
    {
      name: "get_pairings",
      description: "Get the best ingredient pairings for a given ingredient based on shared aroma compounds.",
      inputSchema: {
        type: "object",
        properties: {
          ingredient_id: { type: "string", description: "The ingredient to find pairings for" },
          top_n: { type: "number", description: "Number of pairings to return (default: 10, max: 20)" },
        },
        required: ["ingredient_id"],
      },
    },
    {
      name: "get_variations",
      description: "Get same-role substitute ingredients ranked by aroma similarity, for creating recipe variations. E.g. fennel -> leek/celeriac (turn a fennel velouté into a leek velouté). Proteins swap within meat/seafood families; other ingredients swap within their category.",
      inputSchema: {
        type: "object",
        properties: {
          ingredient_id: { type: "string", description: "The ingredient to find substitutes for" },
          top_n: { type: "number", description: "Number of substitutes (default 6)" },
        },
        required: ["ingredient_id"],
      },
    },
    {
      name: "check_harmony",
      description: "Check the aromatic harmony score between multiple ingredients. Returns a 0-100 score and shared aroma notes.",
      inputSchema: {
        type: "object",
        properties: {
          ingredient_ids: {
            type: "array",
            items: { type: "string" },
            description: "List of ingredient IDs to analyse",
          },
        },
        required: ["ingredient_ids"],
      },
    },
    {
      name: "generate_recipe",
      description: "Generate a complete recipe using aroma-pairing science. Returns ingredients, method, aroma profile, pairing science explanation, and reference real-world recipes from the database.",
      inputSchema: {
        type: "object",
        properties: {
          base_ingredient: { type: "string", description: "The main ingredient ID to build the recipe around" },
          pairing_ingredient: { type: "string", description: "Optional second ingredient to pair with" },
          extra_ingredients: { type: "array", items: { type: "string" }, description: "Additional ingredient IDs to include" },
          cuisine: { type: "string", description: "Cuisine style: Italian, French, Spanish, Mexican, Middle Eastern, Nordic, Asian, Catalan, or 'any'" },
          course: { type: "string", description: "Course type: starter, main, dessert, cocktail, snack, or 'any'" },
          method: { type: "string", description: "Cooking method: roasted, grilled, sautéed, braised, raw, emulsified, fermented, or 'any'" },
          complexity: { type: "string", description: "Recipe complexity: simple, medium, or complex" },
        },
        required: ["base_ingredient"],
      },
    },
    {
      name: "find_recipes",
      description: "Search the recipe database for real recipes containing specific ingredients.",
      inputSchema: {
        type: "object",
        properties: {
          ingredient_ids: { type: "array", items: { type: "string" }, description: "Ingredient IDs to search for" },
          cuisine: { type: "string", description: "Filter by cuisine style" },
          limit: { type: "number", description: "Max results (default 10)" },
        },
        required: ["ingredient_ids"],
      },
    },
    {
      name: "get_aroma_ingredients",
      description: "Get all ingredients that share a specific aroma note.",
      inputSchema: {
        type: "object",
        properties: {
          aroma: { type: "string", description: "Aroma note key: fruity, floral, citrus, green, woody, spicy, smoky, earthy, caramel, nutty, cheesy, sulfurous, marine, minty, fermented, fatty, honey, tropical" },
        },
        required: ["aroma"],
      },
    },
    {
      name: "suggest_drink_pairing",
      description: "Suggest the best wine or beverage pairing for a set of food ingredients, ranked by shared aroma compounds. Returns top matches with the shared aromas.",
      inputSchema: {
        type: "object",
        properties: {
          ingredient_ids: { type: "array", items: { type: "string" }, description: "Food ingredient IDs to pair a drink with" },
          drink_type: { type: "string", description: "Optional filter: 'wine' or 'beverage'. Omit for both." },
          top_n: { type: "number", description: "Number of drink suggestions (default 5)" },
        },
        required: ["ingredient_ids"],
      },
    },
    {
      name: "list_culinary_bases",
      description: "List the foundational culinary base recipes & techniques (stocks, mother sauces, doughs, emulsions, knife cuts, etc.), optionally filtered by category.",
      inputSchema: {
        type: "object",
        properties: {
          category: { type: "string", description: "Optional category filter, e.g. 'Stock', 'Mother Sauce', 'Dough', 'Cold Emulsion', 'Technique'" },
        },
      },
    },
    {
      name: "get_culinary_base",
      description: "Get the full method and ingredients for a foundational culinary base recipe or technique (e.g. béchamel, brown stock, pasta dough, mayonnaise, hollandaise).",
      inputSchema: {
        type: "object",
        properties: {
          id: { type: "string", description: "The base id (e.g. 'base_bechamel') or a search term in its name (e.g. 'hollandaise')" },
        },
        required: ["id"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "get_ingredient": {
      const ing = ingMap[args.id];
      if (!ing) return { content: [{ type: "text", text: `Unknown ingredient: ${args.id}. Use list_ingredients to see available IDs.` }] };
      const pairs = getPairings(args.id, 8);
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            ...ing,
            aromaDetails: ing.aromas.map(a => ({ key: a, ...AROMA_NOTES[a] })),
            topPairings: pairs,
          }, null, 2),
        }],
      };
    }

    case "list_ingredients": {
      let list = INGREDIENTS;
      if (args.category) list = list.filter(i => i.category === args.category);
      if (args.search) {
        const q = args.search.toLowerCase();
        list = list.filter(i => i.name.toLowerCase().includes(q) || i.aromas.some(a => a.includes(q)));
      }
      return {
        content: [{
          type: "text",
          text: JSON.stringify(list.map(i => ({ id: i.id, name: i.name, emoji: i.emoji, category: i.category, aromas: i.aromas })), null, 2),
        }],
      };
    }

    case "get_pairings": {
      const topN = Math.min(args.top_n || 10, 20);
      const pairs = getPairings(args.ingredient_id, topN);
      const ing = ingMap[args.ingredient_id];
      if (!ing) return { content: [{ type: "text", text: `Unknown ingredient: ${args.ingredient_id}` }] };
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            ingredient: { id: ing.id, name: ing.name, emoji: ing.emoji },
            classic: ing.classic,
            surprising: ing.surprising,
            pairings: pairs.map(p => ({
              ...p,
              sharedAromaLabels: p.sharedAromas.map(a => AROMA_NOTES[a]?.label || a),
            })),
            bookPairings: [
              ...(BOOK_PAIRINGS[ing.id]?.named || []),
              ...(BOOK_PAIRINGS[ing.id]?.grid || []),
            ],
          }, null, 2),
        }],
      };
    }

    case "get_variations": {
      const ing = ingMap[args.ingredient_id];
      if (!ing) return { content: [{ type: "text", text: `Unknown ingredient: ${args.ingredient_id}` }] };
      const vars = getVariations(args.ingredient_id, args.top_n || 6);
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            ingredient: { id: ing.id, name: ing.name },
            note: "Swap any of these into a recipe for an aroma-compatible variation.",
            variations: vars,
          }, null, 2),
        }],
      };
    }

    case "check_harmony": {
      const ids = args.ingredient_ids;
      const missing = ids.filter(id => !ingMap[id]);
      if (missing.length) return { content: [{ type: "text", text: `Unknown ingredients: ${missing.join(", ")}` }] };
      const { score, sharedAromas } = scoreHarmony(ids);
      const label = score >= 70 ? "Excellent" : score >= 40 ? "Good" : "Adventurous";
      const verifiedPairs = [];
      for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) {
        const a = ingMap[ids[i]], b = ingMap[ids[j]];
        if (a.pairings.includes(b.id) || b.pairings.includes(a.id)) verifiedPairs.push(`${a.name} + ${b.name}`);
      }
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            ingredients: ids.map(id => `${ingMap[id].emoji} ${ingMap[id].name}`),
            harmonyScore: score,
            label,
            sharedAromaNotes: sharedAromas.map(([a, c]) => ({ aroma: AROMA_NOTES[a]?.label || a, sharedBy: c })),
            verifiedPairings: verifiedPairs,
          }, null, 2),
        }],
      };
    }

    case "generate_recipe": {
      try {
        const recipe = generateRecipe({
          baseId: args.base_ingredient,
          pairId: args.pairing_ingredient,
          cuisine: args.cuisine || "any",
          course: args.course || "any",
          method: args.method || "any",
          complexity: args.complexity || "medium",
          extraIds: args.extra_ingredients || [],
        });
        return { content: [{ type: "text", text: JSON.stringify(recipe, null, 2) }] };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e.message}` }] };
      }
    }

    case "find_recipes": {
      const ids = args.ingredient_ids || [];
      const limit = args.limit || 10;
      const results = RECIPES.filter(r => {
        const rl = r.linked_ingredients || [];
        const overlap = ids.filter(id => rl.includes(id)).length;
        const cuMatch = !args.cuisine || r.cuisine.toLowerCase().includes(args.cuisine.toLowerCase());
        return overlap >= 1 && cuMatch;
      }).sort((a, b) => {
        const oa = (a.linked_ingredients || []).filter(id => ids.includes(id)).length;
        const ob = (b.linked_ingredients || []).filter(id => ids.includes(id)).length;
        return ob - oa;
      }).slice(0, limit);
      return {
        content: [{
          type: "text",
          text: JSON.stringify(results.map(r => ({
            name: r.name,
            cuisine: r.cuisine,
            servings: r.servings || undefined,
            ingredients: r.ingredients,
            method: r.method,
            linkedIngredients: r.linked_ingredients,
          })), null, 2),
        }],
      };
    }

    case "suggest_drink_pairing": {
      const ids = args.ingredient_ids || [];
      const topN = args.top_n || 5;
      const foodIngs = ids.map(id => ingMap[id]).filter(i => i && i.category !== "wine" && i.category !== "beverage");
      if (!foodIngs.length) return { content: [{ type: "text", text: "Provide at least one food ingredient id." }] };
      let drinks = INGREDIENTS.filter(i => i.category === "wine" || i.category === "beverage");
      if (args.drink_type) drinks = drinks.filter(d => d.category === args.drink_type);
      const scored = drinks.filter(d => !ids.includes(d.id)).map(d => {
        let score = 0; const shared = new Set();
        foodIngs.forEach(f => {
          f.aromas.filter(a => d.aromas.includes(a)).forEach(a => { score += 1; shared.add(a); });
          if (f.pairings.includes(d.id) || d.pairings.includes(f.id)) score += 3;
        });
        return { id: d.id, name: d.name, emoji: d.emoji, category: d.category, score,
                 sharedAromas: [...shared].map(a => AROMA_NOTES[a]?.label || a) };
      }).filter(x => x.score > 0).sort((a, b) => b.score - a.score).slice(0, topN);
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            food: foodIngs.map(f => `${f.emoji} ${f.name}`),
            drinkPairings: scored,
          }, null, 2),
        }],
      };
    }

    case "list_culinary_bases": {
      let list = BASES;
      if (args.category) list = list.filter(b => b.category.toLowerCase() === args.category.toLowerCase());
      return {
        content: [{
          type: "text",
          text: JSON.stringify(list.map(b => ({ id: b.id, name: b.name, category: b.category, description: b.description })), null, 2),
        }],
      };
    }

    case "get_culinary_base": {
      const q = (args.id || "").toLowerCase();
      const base = BASES.find(b => b.id === args.id)
        || BASES.find(b => b.name.toLowerCase().includes(q) || b.id.includes(q));
      if (!base) return { content: [{ type: "text", text: `No culinary base found for "${args.id}". Use list_culinary_bases to see available bases.` }] };
      return { content: [{ type: "text", text: JSON.stringify(base, null, 2) }] };
    }

    case "get_aroma_ingredients": {
      const aroma = args.aroma;
      const note = AROMA_NOTES[aroma];
      if (!note) return { content: [{ type: "text", text: `Unknown aroma: ${aroma}. Valid: ${Object.keys(AROMA_NOTES).join(", ")}` }] };
      const ings = INGREDIENTS.filter(i => i.aromas.includes(aroma));
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            aroma: { key: aroma, ...note },
            count: ings.length,
            ingredients: ings.map(i => ({ id: i.id, name: i.name, emoji: i.emoji, category: i.category })),
          }, null, 2),
        }],
      };
    }

    default:
      return { content: [{ type: "text", text: `Unknown tool: ${name}` }] };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
