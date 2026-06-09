#!/usr/bin/env python3
"""
FlavourLab CLI — aroma-based food pairing intelligence.
Pure stdlib, no dependencies. Reads bundled JSON data.

Usage:
  flavourlab.py pairings <ingredient_id> [--top N]
  flavourlab.py harmony <id1> <id2> [<id3> ...]
  flavourlab.py generate <base_id> [--pair ID] [--cuisine X] [--course X] [--method X] [--complexity simple|medium|complex]
  flavourlab.py drink <id1> [<id2> ...] [--type wine|beverage]
  flavourlab.py recipes <id1> [<id2> ...] [--cuisine X] [--limit N]
  flavourlab.py bases [--category X]
  flavourlab.py base <id_or_name>
  flavourlab.py ingredients [--category X] [--search X]
  flavourlab.py aroma <aroma_key>
"""
import json, sys, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
ING = json.load(open(os.path.join(D, "ingredients.json")))
INGREDIENTS = ING["ingredients"]
AROMA = ING["aromas"]
CATLABEL = ING["categoryLabels"]
RECIPES = json.load(open(os.path.join(D, "recipes.json")))
BASES = json.load(open(os.path.join(D, "culinary_bases.json")))
IMAP = {i["id"]: i for i in INGREDIENTS}


def alabel(a):
    return AROMA.get(a, {}).get("label", a)


def pairings(iid, top=10):
    ing = IMAP.get(iid)
    if not ing:
        return {"error": f"Unknown ingredient '{iid}'. Try: ingredients"}
    out = []
    for o in INGREDIENTS:
        if o["id"] == iid:
            continue
        shared = [a for a in ing["aromas"] if a in o["aromas"]]
        verified = o["id"] in ing.get("pairings", []) or iid in o.get("pairings", [])
        if len(shared) >= 2 or verified:
            out.append({
                "id": o["id"], "name": o["name"], "category": o["category"],
                "sharedAromas": [alabel(a) for a in shared],
                "strength": len(shared), "verified": verified,
            })
    out.sort(key=lambda x: (x["strength"], x["verified"]), reverse=True)
    return {"ingredient": ing["name"], "classic": ing.get("classic"),
            "surprising": ing.get("surprising"), "pairings": out[:top]}


def harmony(ids):
    miss = [i for i in ids if i not in IMAP]
    if miss:
        return {"error": f"Unknown: {miss}"}
    freq = {}
    for i in ids:
        for a in IMAP[i]["aromas"]:
            freq[a] = freq.get(a, 0) + 1
    total = mx = 0
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            a, b = IMAP[ids[x]], IMAP[ids[y]]
            sh = [r for r in a["aromas"] if r in b["aromas"]]
            total += len(sh)
            mx += max(len(a["aromas"]), len(b["aromas"]))
    score = min(100, round(total / mx * 320)) if mx else 0
    shared = sorted([(a, c) for a, c in freq.items() if c >= 2], key=lambda x: -x[1])
    return {
        "ingredients": [IMAP[i]["name"] for i in ids],
        "harmonyScore": score,
        "label": "Excellent" if score >= 70 else "Good" if score >= 40 else "Adventurous",
        "sharedAromaNotes": [{"aroma": alabel(a), "sharedBy": c} for a, c in shared],
    }


def drink(ids, dtype=None, top=5):
    food = [IMAP[i] for i in ids if i in IMAP and IMAP[i]["category"] not in ("wine", "beverage")]
    if not food:
        return {"error": "Provide at least one food ingredient id."}
    drinks = [i for i in INGREDIENTS if i["category"] in ("wine", "beverage")]
    if dtype:
        drinks = [d for d in drinks if d["category"] == dtype]
    scored = []
    for d in drinks:
        if d["id"] in ids:
            continue
        sc = 0; sh = set()
        for f in food:
            for a in f["aromas"]:
                if a in d["aromas"]:
                    sc += 1; sh.add(a)
            if d["id"] in f.get("pairings", []) or f["id"] in d.get("pairings", []):
                sc += 3
        if sc:
            scored.append({"id": d["id"], "name": d["name"], "category": d["category"],
                           "score": sc, "sharedAromas": [alabel(a) for a in sh]})
    scored.sort(key=lambda x: -x["score"])
    return {"food": [f["name"] for f in food], "drinkPairings": scored[:top]}


def find_recipes(ids, cuisine=None, limit=10):
    res = []
    for r in RECIPES:
        rl = r.get("linked_ingredients", [])
        ov = len([i for i in ids if i in rl])
        cu = (not cuisine) or cuisine.lower() in r["cuisine"].lower()
        if ov >= 1 and cu:
            res.append((ov, r))
    res.sort(key=lambda x: -x[0])
    return [{"name": r["name"], "cuisine": r["cuisine"], "servings": r.get("servings", ""),
             "ingredients": r["ingredients"], "method": r.get("method", [])}
            for _, r in res[:limit]]


SWEET_ONLY = {"chocolate", "vanilla"}
SUPPORT_BONUS = {"herb": 3, "spice": 3, "other": 2, "vegetable": 2, "dairy": 1, "fruit": 1}


def pick_fillers(core, count, course):
    """Coherent supporting cast: complements the WHOLE core, no extra proteins/sweets."""
    if count <= 0:
        return []
    core_ids = {i["id"] for i in core}
    proteins = sum(1 for i in core if i["category"] == "protein")
    dessert, drink_c = course == "dessert", course == "cocktail"
    need = (len(core) + 1) // 2
    scored = []
    for o in INGREDIENTS:
        if o["id"] in core_ids:
            continue
        if proteins >= 1 and o["category"] == "protein":
            continue
        if o["category"] in ("wine", "beverage"):
            continue
        if not (dessert or drink_c) and o["id"] in SWEET_ONLY:
            continue
        pc = at = vf = 0
        for c in core:
            sh = [a for a in c["aromas"] if a in o["aromas"]]
            at += len(sh)
            is_pair = o["id"] in c.get("pairings", []) or c["id"] in o.get("pairings", [])
            if sh or is_pair:
                pc += 1
            if is_pair:
                vf += 1
        if pc >= need:
            scored.append((pc, at + vf * 3 + SUPPORT_BONUS.get(o["category"], 0), o))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [o for _, _, o in scored[:count]]


def generate(base_id, pair=None, cuisine="any", course="any", method="any", complexity="medium", extra=None):
    base = IMAP.get(base_id)
    if not base:
        return {"error": f"Unknown base '{base_id}'"}
    extra = extra or []
    count = {"simple": 5, "complex": 10}.get(complexity, 7)
    sel = [base] + ([IMAP[pair]] if pair and pair in IMAP else []) + [IMAP[e] for e in extra if e in IMAP]
    sel += pick_fillers(sel, count - len(sel), course)
    freq = {}
    for i in sel:
        for a in i["aromas"]:
            freq[a] = freq.get(a, 0) + 1
    top = [a for a, _ in sorted(freq.items(), key=lambda x: -x[1])[:4]]
    refs = find_recipes([i["id"] for i in sel], None if cuisine == "any" else cuisine, 4)
    dr = drink([i["id"] for i in sel], None, 1)
    sci = None
    p2 = IMAP.get(pair)
    if p2:
        sa = [a for a in base["aromas"] if a in p2["aromas"]]
        sci = (f"{base['name']} and {p2['name']} share {len(sa)} aroma molecule(s): "
               f"{', '.join(alabel(a) for a in sa)}.")
    return {
        "name": _name(base, p2, cuisine, course, method),
        "cuisine": "Modern" if cuisine == "any" else cuisine,
        "course": course, "method": method, "complexity": complexity,
        "ingredients": [{"name": i["name"], "role": "base" if k == 0 else "pairing" if (k == 1 and p2) else "supporting"}
                        for k, i in enumerate(sel)],
        "aromaProfile": [alabel(a) for a in top],
        "pairingScience": sci,
        "harmonyScore": harmony([i["id"] for i in sel])["harmonyScore"],
        "suggestedDrink": dr["drinkPairings"][0] if dr.get("drinkPairings") else None,
        "referenceRecipes": [{"name": r["name"], "cuisine": r["cuisine"]} for r in refs],
    }


def _name(base, pair, cuisine, course, method):
    m = {"roasted": "Roasted", "grilled": "Grilled", "sautéed": "Sautéed", "braised": "Braised",
         "raw": "Raw", "emulsified": "Emulsified", "fermented": "Cured"}.get(method, "")
    if course == "cocktail":
        return f"{base['name']}{' & ' + pair['name'] if pair else ''} Cocktail"
    if course == "dessert":
        return f"{m} {base['name']}{' with ' + pair['name'] if pair else ''} Dessert".strip()
    if not pair:
        return f"{m} {base['name']}".strip()
    return f"{m} {base['name']} with {pair['name']}".strip()


def main():
    p = argparse.ArgumentParser(description="FlavourLab CLI")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("pairings"); a.add_argument("id"); a.add_argument("--top", type=int, default=10)
    a = sub.add_parser("harmony"); a.add_argument("ids", nargs="+")
    a = sub.add_parser("generate"); a.add_argument("base"); a.add_argument("--pair"); a.add_argument("--cuisine", default="any")
    a.add_argument("--course", default="any"); a.add_argument("--method", default="any"); a.add_argument("--complexity", default="medium")
    a.add_argument("--extra", nargs="*", default=[])
    a = sub.add_parser("drink"); a.add_argument("ids", nargs="+"); a.add_argument("--type"); a.add_argument("--top", type=int, default=5)
    a = sub.add_parser("recipes"); a.add_argument("ids", nargs="+"); a.add_argument("--cuisine"); a.add_argument("--limit", type=int, default=10)
    a = sub.add_parser("bases"); a.add_argument("--category")
    a = sub.add_parser("base"); a.add_argument("id")
    a = sub.add_parser("ingredients"); a.add_argument("--category"); a.add_argument("--search")
    a = sub.add_parser("aroma"); a.add_argument("key")

    args = p.parse_args()
    if args.cmd == "pairings":
        out = pairings(args.id, args.top)
    elif args.cmd == "harmony":
        out = harmony(args.ids)
    elif args.cmd == "generate":
        out = generate(args.base, args.pair, args.cuisine, args.course, args.method, args.complexity, args.extra)
    elif args.cmd == "drink":
        out = drink(args.ids, args.type, args.top)
    elif args.cmd == "recipes":
        out = find_recipes(args.ids, args.cuisine, args.limit)
    elif args.cmd == "bases":
        out = [{"id": b["id"], "name": b["name"], "category": b["category"], "description": b["description"]}
               for b in BASES if not args.category or b["category"].lower() == args.category.lower()]
    elif args.cmd == "base":
        q = args.id.lower()
        b = next((x for x in BASES if x["id"] == args.id), None) or \
            next((x for x in BASES if q in x["name"].lower() or q in x["id"]), None)
        out = b or {"error": f"No base for '{args.id}'"}
    elif args.cmd == "ingredients":
        lst = INGREDIENTS
        if args.category:
            lst = [i for i in lst if i["category"] == args.category]
        if args.search:
            s = args.search.lower()
            lst = [i for i in lst if s in i["name"].lower() or any(s in a for a in i["aromas"])]
        out = [{"id": i["id"], "name": i["name"], "category": i["category"], "aromas": i["aromas"]} for i in lst]
    elif args.cmd == "aroma":
        if args.key not in AROMA:
            out = {"error": f"Unknown aroma. Valid: {list(AROMA)}"}
        else:
            out = {"aroma": AROMA[args.key]["label"],
                   "ingredients": [{"id": i["id"], "name": i["name"]} for i in INGREDIENTS if args.key in i["aromas"]]}
    else:
        p.print_help(); return
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
