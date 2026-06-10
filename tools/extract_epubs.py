#!/usr/bin/env python3
"""
Generic EPUB recipe extractor for FlavourLab.
Works across heterogeneous cookbook structures by detecting:
  - recipe titles (headings followed by ingredients + method)
  - ingredient lines (measurement patterns)
  - method/instruction paragraphs
Keeps ONLY English-language recipes (language heuristic).
No book titles or author names are retained — recipes + methods only.
"""
import zipfile, re, os, json, sys
from bs4 import BeautifulSoup
from collections import Counter

BOOKS_DIR = '/Users/usuario/Documents/06_Libros/Cocina/'
OUT = '/Users/usuario/foodpairing-lab/data/recipes_epub.json'

# ── Measurement / ingredient signals ──────────────────────────────────────────
UNIT_RE = re.compile(
    r'\b(\d+[\d/.,½¼¾⅓⅔⅛\s-]*)\s*'
    r'(g|kg|ml|l|oz|lb|lbs|cup|cups|tbsp|tsp|tablespoon|teaspoon|'
    r'gram|grams|ounce|ounces|pound|pounds|litre|liter|litres|liters|'
    r'clove|cloves|slice|slices|pinch|pinches|handful|sprig|sprigs|'
    r'bunch|bunches|stick|sticks|can|cans|knob|dash|quart|pint|fl\s?oz)\b',
    re.IGNORECASE)

FRACTION_START_RE = re.compile(r'^\s*[\d½¼¾⅓⅔⅛]')

# ── Language detection (English vs not) ───────────────────────────────────────
EN_WORDS = set("the and with a of to in for until add then over heat oil salt "
               "pepper water cook cooking minutes pan large medium small until "
               "remove from into about your you it is are this serve set aside".split())
ES_WORDS = set("el la los las de con un una para por en y que se al del como "
               "aceite sal agua cocer fuego añadir minutos hasta luego".split())
FR_WORDS = set("le la les des un une de avec pour dans et que au du sur "
               "huile sel eau cuire feu ajouter minutes jusqu puis".split())

def detect_lang(text):
    words = re.findall(r'\b[a-záéíóúàèùçñ]+\b', text.lower())[:200]
    if not words:
        return 'unknown'
    en = sum(1 for w in words if w in EN_WORDS)
    es = sum(1 for w in words if w in ES_WORDS)
    fr = sum(1 for w in words if w in FR_WORDS)
    if en >= es and en >= fr and en >= 3:
        return 'en'
    if es > en or fr > en:
        return 'other'
    return 'en' if en >= 2 else 'unknown'

# ── Ingredient → FlavourLab ingredient ID mapping ─────────────────────────────
INGREDIENT_MAP = {
    'kiwi':'kiwi','apple':'apple','strawberr':'strawberry','watermelon':'watermelon',
    'lemon':'lemon','lime':'lime','blueberr':'blueberry','apricot':'apricot',
    'orange':'orange','mango':'mango','pineapple':'pineapple','raspberr':'raspberry',
    'banana':'banana','pear':'pear','grapefruit':'grapefruit','avocado':'avocado',
    'pomegranate':'pomegranate','peach':'peach','celeriac':'celeriac',
    'cauliflower':'cauliflower','bell pepper':'red-bell-pepper','garlic':'garlic',
    'sweet potato':'sweet-potato','butternut':'butternut-squash','beetroot':'beetroot',
    'beet ':'beetroot','carrot':'carrot','tomato':'tomato','green bean':'green-beans',
    'cucumber':'cucumber','artichoke':'artichoke','basil':'basil','coriander':'coriander',
    'cilantro':'coriander','cinnamon':'cinnamon','ginger':'ginger','lemongrass':'lemongrass',
    'cumin':'cumin','black pepper':'black-pepper','peppercorn':'black-pepper',
    'cardamom':'cardamom','sesame':'sesame','jasmine':'jasmine','elderflower':'elderflower',
    'salmon':'fish','cod':'fish','sole':'fish','tuna':'fish','halibut':'fish','sea bass':'fish',
    'mackerel':'fish','trout':'fish','anchov':'fish','sardine':'fish',
    'oyster':'oyster','lobster':'crustaceans','prawn':'crustaceans','shrimp':'crustaceans',
    'crab':'crustaceans','langoustine':'crustaceans','scallop':'crustaceans',
    'pork':'pork','bacon':'pork','chicken':'chicken','duck':'chicken','turkey':'chicken',
    'lamb':'lamb','beef':'beef','veal':'beef','ham':'iberico-ham','prosciutto':'iberico-ham',
    'chorizo':'chorizo','goat cheese':'cheese-goat','goats cheese':'cheese-goat',
    'gorgonzola':'cheese-blue','blue cheese':'cheese-blue','brie':'cheese-brie',
    'parmesan':'cheese-parmesan','parmigiano':'cheese-parmesan','pecorino':'cheese-parmesan',
    'yogurt':'yogurt','yoghurt':'yogurt','tequila':'tequila','cognac':'cognac',
    'gin':'gin','rum':'rum','bourbon':'bourbon','whiskey':'bourbon','coffee':'coffee',
    'espresso':'coffee','tea':'tea','chocolate':'chocolate','cocoa':'chocolate',
    'vanilla':'vanilla','truffle':'truffle','olive oil':'olive-oil','balsamic':'balsamic',
    'soy sauce':'soy-sauce','soya':'soy-sauce','coconut':'coconut','seaweed':'seaweed',
    'nori':'seaweed','kombu':'seaweed','wakame':'seaweed','bergamot':'bergamot',
    'hazelnut':'hazelnut','almond':'almond','rye':'sourdough-rye','miso':'miso',
    'kimchi':'kimchi','mushroom':'shiitake','shiitake':'shiitake',
}

def link_ingredients(text):
    t = text.lower()
    found = []
    for key, iid in INGREDIENT_MAP.items():
        if key in t and iid not in found:
            found.append(iid)
    return found[:10]

# ── Cuisine inference from filename (kept generic, no titles stored) ──────────
def infer_cuisine(fname):
    f = fname.lower()
    table = [
        (['thai','thailand'], 'Thai'), (['china','asian','ramen','momofuku','izakaya','rintaro'], 'Asian'),
        (['mexic','oaxaca','taco','tex_mex','tex mex'], 'Mexican'),
        (['india','pakistan'], 'Indian'), (['cambodia'], 'Cambodian'),
        (['lebanese','mezze','mez','middle_eastern','middle eastern','arabesque'], 'Middle Eastern'),
        (['greek','greekish'], 'Greek'), (['german'], 'German'),
        (['italian','pasta','pizza','mozza','italian_coastal','italian coastal','hazan'], 'Italian'),
        (['france','french','ferrandi','bocuse','ducasse','pepin','boulud','herme','etchebest','escoffier','robuchon','ritz'], 'French'),
        (['spain','spanish','arzak','dacosta','tapas','bravazo','disfrutar','tickets','abac','celler','ruscalleda'], 'Spanish'),
        (['cajun','louisiana','america','downton'], 'American'),
        (['colombia'], 'Colombian'), (['noma','faviken','nordic'], 'Nordic'),
        (['bread','sourdough','baker','baking','sift','patisserie','gelato','gelupo','paleo'], 'Baking'),
        (['fish','seafood','whole_fish','whole fish'], 'Seafood'),
        (['vegetable','passard'], 'Vegetable'), (['ferment','koji','noma_guide'], 'Fermentation'),
        (['meat','charcuterie','butcher'], 'Meat'), (['cocktail','wine','aguardiente','licor'], 'Drinks'),
    ]
    for keys, cuisine in table:
        if any(k in f for k in keys):
            return cuisine
    return 'International'

# ── Core extraction ───────────────────────────────────────────────────────────
def get_html_files(z):
    # Use spine order via OPF if possible, else sorted html files
    htmls = [n for n in z.namelist() if n.lower().endswith(('.xhtml','.html','.htm'))]
    return sorted(htmls)

def _cls(el):
    c = el.get('class')
    if not c:
        return ''
    # normalise: lowercase, strip separators so 'recipe-head' == 'recipehead'
    return ' '.join(c).lower().replace('-', '').replace('_', '')

TITLE_CLASSES = ('recipetitle', 'rectitle', 'ilsubheader', 'recipehead',
                 'repttl', 'recipename', 'titlerecipe', 'recttl', 'recipehd',
                 'recipettl', 'dishname')
ING_CLASSES = ('ingred', 'ilitem', 'recipeing', 'hang', 'inglist', 'ingtxt')
METHOD_CLASSES = ('method', 'step', 'instruction', 'direction', 'restxt', 'prep')
SERV_RE = re.compile(r'\b(serves|makes|yields?|portions?)\b', re.I)

def _looks_ingredient(el, txt):
    if len(txt) > 170:
        return False
    cls = _cls(el)
    if any(k in cls for k in ING_CLASSES):
        return True
    if el.name == 'li' and len(txt) < 170:
        return True
    return bool(UNIT_RE.search(txt) or FRACTION_START_RE.match(txt))

def _looks_method(el, txt):
    cls = _cls(el)
    if any(k in cls for k in METHOD_CLASSES):
        return len(txt) > 25
    return len(txt) > 70

def _looks_heading(el, txt):
    cls = _cls(el)
    class_title = any(k in cls for k in TITLE_CLASSES)
    if class_title:
        return 3 < len(txt) < 75          # trust the class even if ALL-CAPS
    if el.name in ('h1', 'h2', 'h3', 'h4'):
        if not (3 < len(txt) < 70):
            return False
        if txt.isupper() and len(txt) > 28:   # likely a section banner
            return False
        return True
    return False

BLOCK_TAGS = ['p', 'li', 'div', 'h1', 'h2', 'h3', 'h4']

def extract_from_html(html, cuisine, book_id, counter):
    recs = []
    soup = BeautifulSoup(html, 'lxml')
    for t in soup(['script', 'style']):
        t.decompose()

    anchors = [el for el in soup.find_all(BLOCK_TAGS)
               if (txt := el.get_text(' ', strip=True)) and _looks_heading(el, txt)]

    for h in anchors:
        title = h.get_text(' ', strip=True)
        ings, method, servings, desc = [], [], '', ''
        seen_ing = False
        for el in h.find_all_next(BLOCK_TAGS):
            t2 = el.get_text(' ', strip=True)
            if not t2:
                continue
            if _looks_heading(el, t2) and el is not h:
                break
            # leaf-ish blocks only (avoid nested-div double counting)
            if el.find(BLOCK_TAGS):
                continue
            cls = _cls(el)
            # servings / yield line (allow leading symbols like '° Makes 1 cup')
            if (SERV_RE.search(t2[:24]) or 'yield' in cls or 'serving' in cls) and len(t2) < 60:
                if not servings:
                    servings = re.sub(r'^[^A-Za-z]+', '', t2)
                continue
            if _looks_ingredient(el, t2):
                ings.append(t2)
                seen_ing = True
            elif _looks_method(el, t2):
                if seen_ing:
                    method.append(t2)            # real instructions follow ingredients
                elif not desc and 'headnote' not in cls:
                    desc = t2                    # first long para before ings = description
                elif 'headnote' in cls and not desc:
                    desc = t2
            if len(method) > 14 or len(ings) > 28:
                break
        if len(ings) >= 3 and len(method) >= 1:
            full = title + ' ' + ' '.join(ings) + ' ' + ' '.join(method)
            if detect_lang(full) != 'en':
                continue
            # fix ALL-CAPS titles for display
            disp = title.title() if title.isupper() else title
            counter[0] += 1
            recs.append({
                'id': f"{book_id}_{counter[0]}",
                'name': disp,
                'cuisine': cuisine,
                'servings': servings,
                'description': re.sub(r'\s+', ' ', desc)[:280],
                'ingredients': [re.sub(r'\s+', ' ', i)[:140] for i in ings[:18]],
                'method': [re.sub(r'\s+', ' ', m)[:450] for m in method[:10]],
                'linked_ingredients': link_ingredients(full),
                'source': 'epub',
            })
    return recs

def extract_book(path, fname):
    cuisine = infer_cuisine(fname)
    book_id = 'e' + str(abs(hash(fname)) % 100000)
    counter = [0]
    all_recs = []
    try:
        z = zipfile.ZipFile(path)
        for hf in get_html_files(z):
            try:
                html = z.read(hf).decode('utf-8','ignore')
            except Exception:
                continue
            if len(html) < 300:
                continue
            all_recs.extend(extract_from_html(html, cuisine, book_id, counter))
    except Exception as e:
        print(f"  ! error {fname[:40]}: {e}", file=sys.stderr)
    return all_recs

def main():
    epubs = [f for f in os.listdir(BOOKS_DIR) if f.lower().endswith('.epub')]
    print(f"Found {len(epubs)} EPUBs")
    all_recipes = []
    seen = set()
    for i, fname in enumerate(sorted(epubs), 1):
        recs = extract_book(BOOKS_DIR + fname, fname)
        # dedupe by name
        kept = 0
        for r in recs:
            key = r['name'].lower().strip()
            if key in seen or len(key) < 4:
                continue
            seen.add(key)
            all_recipes.append(r)
            kept += 1
        print(f"[{i}/{len(epubs)}] {kept:4d} EN recipes  ·  {infer_cuisine(fname):14s}  ·  {fname[:42]}")
    print(f"\nTOTAL English recipes from EPUBs: {len(all_recipes)}")
    by_c = Counter(r['cuisine'] for r in all_recipes)
    for c, n in sorted(by_c.items(), key=lambda x:-x[1]):
        print(f"  {c:16s} {n}")
    with open(OUT, 'w') as f:
        json.dump(all_recipes, f, ensure_ascii=False, indent=1)
    print(f"\nSaved → {OUT}")

if __name__ == '__main__':
    main()
