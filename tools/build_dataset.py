#!/usr/bin/env python3
"""
Merge EPUB + PDF recipes, clean junk, fix ingredient linking with word
boundaries, and emit the unified FlavourLab recipe dataset + culinary bases.
All output is English-only, no book/author attribution.
"""
import json, re, os
from collections import Counter

BASE = '/Users/usuario/foodpairing-lab'

# ── Word-boundary ingredient matcher (fixes 'tea' in 'steam' etc.) ────────────
INGREDIENT_MAP = {
    r'kiwi':'kiwi', r'apple':'apple', r'strawberr\w*':'strawberry', r'watermelon':'watermelon',
    r'lemon':'lemon', r'lime':'lime', r'blueberr\w*':'blueberry', r'apricot':'apricot',
    r'orange':'orange', r'mango':'mango', r'pineapple':'pineapple', r'raspberr\w*':'raspberry',
    r'banana':'banana', r'pear':'pear', r'grapefruit':'grapefruit', r'avocado':'avocado',
    r'pomegranate':'pomegranate', r'peach':'peach', r'celeriac':'celeriac',
    r'cauliflower':'cauliflower', r'bell pepper':'red-bell-pepper', r'garlic':'garlic',
    r'sweet potato':'sweet-potato', r'butternut':'butternut-squash', r'beetroot':'beetroot',
    r'beet':'beetroot', r'carrot':'carrot', r'tomato\w*':'tomato', r'green bean':'green-beans',
    r'cucumber':'cucumber', r'artichoke':'artichoke', r'basil':'basil',
    r'coriander':'coriander', r'cilantro':'coriander', r'cinnamon':'cinnamon',
    r'ginger':'ginger', r'lemongrass':'lemongrass', r'cumin':'cumin',
    r'black pepper':'black-pepper', r'peppercorn\w*':'black-pepper', r'cardamom':'cardamom',
    r'sesame':'sesame', r'jasmine':'jasmine', r'elderflower':'elderflower',
    r'salmon':'fish', r'\bcod\b':'fish', r'\bsole\b':'fish', r'tuna':'fish', r'halibut':'fish',
    r'sea bass':'fish', r'mackerel':'fish', r'trout':'fish', r'anchov\w*':'fish', r'sardine':'fish',
    r'oyster':'oyster', r'lobster':'crustaceans', r'prawn':'crustaceans', r'shrimp':'crustaceans',
    r'\bcrab\b':'crustaceans', r'langoustine':'crustaceans', r'scallop':'crustaceans',
    r'\bpork\b':'pork', r'bacon':'pork', r'chicken':'chicken', r'\bduck\b':'duck',
    r'turkey':'chicken', r'\blamb\b':'lamb', r'\bmutton\b':'lamb', r'\bbeef\b':'beef',
    r'\bveal\b':'beef', r'\bsteak\b':'beef', r'\bbrisket\b':'beef',
    r'\bham\b':'iberico-ham', r'prosciutto':'iberico-ham', r'chorizo':'chorizo',
    r'goat\'?s? cheese':'cheese-goat', r'gorgonzola':'cheese-blue', r'blue cheese':'cheese-blue',
    r'\bbrie\b':'cheese-brie', r'parmesan':'cheese-parmesan', r'parmigiano':'cheese-parmesan',
    r'pecorino':'cheese-parmesan', r'yogurt':'yogurt', r'yoghurt':'yogurt', r'tequila':'tequila',
    r'cognac':'cognac', r'\bgin\b':'gin', r'\brum\b':'rum', r'bourbon':'bourbon',
    r'whiskey':'bourbon', r'coffee':'coffee', r'espresso':'coffee', r'\btea\b':'tea',
    r'chocolate':'chocolate', r'cocoa':'chocolate', r'vanilla':'vanilla', r'truffle':'truffle',
    r'olive oil':'olive-oil', r'balsamic':'balsamic', r'soy sauce':'soy-sauce', r'soya':'soy-sauce',
    r'coconut':'coconut', r'seaweed':'seaweed', r'\bnori\b':'seaweed', r'kombu':'seaweed',
    r'wakame':'seaweed', r'bergamot':'bergamot', r'hazelnut':'hazelnut', r'almond':'almond',
    r'\brye\b':'sourdough-rye', r'\bmiso\b':'miso', r'kimchi':'kimchi',
    r'mushroom':'shiitake', r'shiitake':'shiitake', r'porcini':'shiitake', r'cep\b':'shiitake',
    # newly-added ingredients
    r'fennel':'fennel', r'\bleek':'leek', r'onion':'onion', r'shallot':'onion',
    r'potato':'potato', r'\begg\b':'egg', r'\beggs\b':'egg', r'cherry|cherries':'cherry',
    r'\bfig\b|\bfigs\b':'fig', r'honey':'honey', r'\bmint\b':'mint', r'rosemary':'rosemary',
    r'thyme':'thyme', r'cheddar':'cheese-cheddar', r'\bbutter\b':'butter', r'\bcream\b':'cream',
    # wines / drinks
    r'cabernet':'cabernet-sauvignon', r'pinot noir':'pinot-noir', r'syrah|shiraz':'syrah',
    r'chardonnay':'chardonnay', r'riesling':'riesling', r'champagne':'champagne',
    r'\bport\b':'port', r'sherry':'sherry', r'\bsake\b':'sake', r'\bcider\b':'cider',
    r'vermouth':'vermouth',
    # newly-added vegetables / herbs / spices / nuts
    r'rhubarb':'rhubarb', r'asparagus':'asparagus', r'celery':'celery',
    r'aubergine|eggplant':'aubergine', r'broccoli':'broccoli', r'cabbage':'cabbage',
    r'parsnip':'parsnip', r'\bswede\b|rutabaga':'swede', r'watercress':'watercress',
    r'\bdill\b':'dill', r'parsley':'parsley', r'\bsage\b':'sage',
    r'\banise\b|aniseed|star anise':'anise', r'nutmeg':'nutmeg', r'\bclove\b|cloves':'clove',
    r'saffron':'saffron', r'juniper':'juniper', r'horseradish':'horseradish',
    r'walnut':'walnut', r'chestnut':'chestnut', r'peanut':'peanut', r'\bcaper':'caper',
    r'anchov':'anchovy', r'caviar':'caviar',
    # remaining thesaurus flavors
    r'\bgrape\b|grapes':'grape', r'rose water|rosewater|rose petal':'rose',
    r'white chocolate':'white-chocolate', r'\bpea\b|peas|petit pois':'pea',
    r'blackcurrant|black currant|cassis':'blackcurrant', r'blackberr':'blackberry',
    r'\bmelon\b|cantaloupe|honeydew':'melon', r'black pudding|blood sausage':'black-pudding',
    r'\bliver\b|foie gras':'liver',
    # common spices
    r'paprika|piment[oó]n':'paprika', r'turmeric':'turmeric', r'coriander seed':'coriander-seed',
    r'allspice':'allspice', r'caraway':'caraway', r'\bmustard\b':'mustard',
    r'\bbay leaf|bay leaves|\bbay\b':'bay-leaf', r'sumac':'sumac', r'fenugreek':'fenugreek',
    # common herbs
    r'oregano':'oregano', r'tarragon':'tarragon', r'chive':'chives',
}
COMPILED = [(re.compile(r'\b' + pat if not pat.startswith(r'\b') else pat, re.I), iid)
            for pat, iid in INGREDIENT_MAP.items()]

def link_ingredients(text):
    found = []
    for rx, iid in COMPILED:
        if iid not in found and rx.search(text):
            found.append(iid)
    return found[:12]

# ── Junk title filter ─────────────────────────────────────────────────────────
JUNK_TITLE = re.compile(
    r'^(yields?|makes?|serves?|for \d|preparation|ingredients?|method|directions?|'
    r'note|tip|variation|step \d|chapter|introduction|about|contents|index|'
    r'measurements?|how to|the basics?)\b', re.I)

def is_good_recipe(r):
    name = (r.get('name') or '').strip()
    if not (4 <= len(name) <= 72):
        return False
    if JUNK_TITLE.match(name):
        return False
    if name.isupper() and len(name) > 28:
        return False
    if sum(c.isdigit() for c in name) > 4:
        return False
    ings = r.get('ingredients') or r.get('ingredients_raw') or []
    if len(ings) < 3:
        return False
    method = r.get('method') or []
    if isinstance(method, str):
        method = [method]
    if len(method) < 1:
        return False
    return True

# ── Normalise a record to unified schema ──────────────────────────────────────
def normalise(r):
    name = re.sub(r'\s+', ' ', r['name']).strip()
    name = re.sub(r'\s+(MAKES|SERVES|YIELDS?|FOR)\b.*$', '', name, flags=re.I).strip(' .,–-')
    ings = r.get('ingredients') or r.get('ingredients_raw') or []
    method = r.get('method') or []
    if isinstance(method, str):
        method = [method]
    full = name + ' ' + ' '.join(ings) + ' ' + ' '.join(method)
    return {
        'id': r['id'],
        'name': name,
        'cuisine': r.get('cuisine', 'International'),
        'servings': re.sub(r'\s+', ' ', r.get('servings', '')).strip()[:60],
        'description': re.sub(r'\s+', ' ', r.get('description', '')).strip()[:300],
        'ingredients': [re.sub(r'\s+', ' ', i).strip()[:140] for i in ings[:18] if i.strip()],
        'method': [re.sub(r'\s+', ' ', m).strip()[:450] for m in method[:10] if m.strip()],
        'linked_ingredients': link_ingredients(full),
        'source': 'book',  # no per-book attribution retained
    }

def main():
    epub = json.load(open(f'{BASE}/data/recipes_epub.json'))
    pdf = json.load(open(f'{BASE}/data/recipes_pdf.json'))
    print(f"EPUB raw: {len(epub)}  ·  PDF raw: {len(pdf)}")

    merged, seen = [], set()
    for r in epub + pdf:
        if not is_good_recipe(r):
            continue
        rec = normalise(r)
        key = rec['name'].lower()
        if key in seen or len(key) < 4:
            continue
        if not rec['linked_ingredients']:
            continue
        seen.add(key)
        merged.append(rec)

    print(f"Merged clean recipes: {len(merged)}")
    by_c = Counter(r['cuisine'] for r in merged)
    for c, n in sorted(by_c.items(), key=lambda x: -x[1]):
        print(f"  {c:16s} {n}")

    out = f'{BASE}/data/recipes.json'
    json.dump(merged, open(out, 'w'), ensure_ascii=False, indent=1)
    json.dump(merged, open(f'{BASE}/public/recipes.json', 'w'), ensure_ascii=False, indent=1)
    print(f"\nSaved → {out} (+ public mirror)")

if __name__ == '__main__':
    main()
