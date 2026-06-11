#!/usr/bin/env python3
"""
Post-process recipes.json:
  1. QA — drop garbled titles / sentence-fragments / non-recipes
  2. Re-classify cuisine from the recipe's own text signals (not the book name),
     using the book cuisine only as a weak prior.
Writes cleaned recipes.json (+ public/skill mirrors).
"""
import json, re
from collections import Counter

BASE = '/Users/usuario/foodpairing-lab'

# ── cuisine signal lexicon (token → cuisine) ──────────────────────────────────
SIGNALS = {
 'Italian': ['pasta','risotto','parmesan','parmigiano','pecorino','mozzarella','basil pesto',
   'gnocchi','polenta','prosciutto','guanciale','ricotta','mascarpone','balsamic','tagliatelle',
   'spaghetti','lasagne','focaccia','burrata','nduja','passata','soffritto'],
 'Mexican': ['tortilla','taco','salsa','jalapeno','jalapeño','chipotle','masa','mole','tomatillo',
   'epazote','guajillo','ancho chil','poblano','cotija','queso fresco','nixtamal','elote',
   'comal','crema','guacamole','adobo'],
 'Middle Eastern': ['tahini','sumac','za','pomegranate molasses','bulgur','freekeh','harissa',
   'labneh','baharat','halloumi','filo','tabbouleh','hummus','pita','rose water','orange blossom',
   'pul biber','dukkah','ras el hanout','preserved lemon'],
 'Thai': ['fish sauce','lemongrass','galangal','kaffir','makrut','thai basil','palm sugar',
   'coconut milk','bird','tom yum','pad ','nam pla','shrimp paste','green curry','red curry'],
 'Asian': ['soy sauce','miso','mirin','dashi','sake','gochujang','kimchi','sesame oil','rice wine',
   'hoisin','oyster sauce','shaoxing','bok choy','wok','nori','wasabi','doenjang','ramen','dumpling',
   'star anise','five spice','szechuan','sichuan'],
 'Indian': ['garam masala','turmeric','cumin seed','curry leaf','ghee','paneer','tandoor','naan',
   'cardamom pod','basmati','fenugreek','asafoetida','dal','masala','chaat'],
 'French': ['beurre','crème fra','crème','confit','sauce velouté','demi-glace','mirepoix','roux',
   'shallot','tarragon','dijon','baguette','gruyère','gruyere','bouquet garni','sous vide',
   'beurre blanc','en croute','julienne'],
 'Greek': ['feta','filo','ouzo','phyllo','kalamata','oregano','dolma','tzatziki','greek yogurt',
   'halloumi','retsina','horta'],
 'Nordic': ['rye bread','dill','juniper','lingonberry','cloudberry','aquavit','rye','smoked',
   'pickled herring','cured','sea buckthorn','birch'],
 'Spanish': ['chorizo','jamón','jamon','pimentón','pimenton','manchego','sofrito','paella','sherry',
   'saffron','piquillo','romesco','alioli','gazpacho','serrano','azafrán'],
 'British': ['cheddar','clotted cream','suet','black pudding','treacle','golden syrup','custard',
   'crumpet','scone','marmite','worcestershire','double cream','sticky toffee'],
 'American': ['bourbon','maple syrup','cornbread','grits','buttermilk','barbecue','pecan',
   'cajun','creole','gumbo','jambalaya','peanut butter','marshmallow'],
 'Baking': ['plain flour','all-purpose flour','baking powder','baking soda','yeast','sourdough',
   'caster sugar','icing sugar','egg white','egg yolk','vanilla extract','butter, softened',
   'self-raising','proof','knead','dough'],
}
COMPILED = {c: [re.compile(r'\b' + re.escape(t), re.I) for t in toks] for c, toks in SIGNALS.items()}

# book-prior: keep these book-level cuisines when text is inconclusive
PRIOR_OK = set(SIGNALS) | {'International','Catalan','Cambodian','Colombian','Seafood',
                           'Pastry','Drinks','Garde Manger','Fermentation','Meat'}

def classify(rec):
    text = (rec['name'] + ' ' + ' '.join(rec['ingredients']) + ' ' +
            ' '.join(rec.get('method', []))).lower()
    scores = {}
    for c, rxs in COMPILED.items():
        s = sum(1 for rx in rxs if rx.search(text))
        if s:
            scores[c] = s
    prior = rec.get('cuisine', 'International')
    if prior == 'Spanish Avant-Garde':
        prior = 'Spanish'
    best = max(scores, key=scores.get) if scores else None
    top = scores.get(best, 0)
    prior_score = scores.get(prior, 0)
    # override the book prior only on STRONG evidence (2+ distinct signals)
    # and only when the prior isn't equally supported
    if best and top >= 2 and top > prior_score:
        return best
    if prior in PRIOR_OK:
        return prior
    return best if best else 'International'

# ── QA: reject junk titles ────────────────────────────────────────────────────
JUNK_TITLE = re.compile(
    r'^(creation|others?|water|drain|when |therefore|step|method|note|tip|makes?|serves?|'
    r'preheat|combine|place|add |mix |stir |heat |bring |meanwhile|for the|put |pour|'
    r'remove|season|cook|cut |chop|slice|the secret|it |this |that |these |a |an |in |'
    r'with |to |into |over |from |once |after |before |if )', re.I)
SENTENCE_HINT = re.compile(r'\b(we|i|you|it|they|was|were|are|is|will|would|could|because|'
                           r'finally|surprise|amazed|thought)\b', re.I)

GENERIC_HEADER = {'layering flavour','fish and shellfish','others','salads','soups','desserts',
                  'sauces','starters','mains','sides','breakfast','drinks','basics','vegetables',
                  'meat','poultry','seafood','baking','pastry','snacks','condiments'}
FRAGMENT_WORDS = re.compile(r'^(salt|pinch|pepper|sugar|flour|water|oil|butter|region|grated|'
                            r'ground|chopped|sliced|fresh|dried|de |la |el |al )', re.I)

def good_title(name):
    n = name.strip()
    if not (4 <= len(n) <= 55):
        return False
    if JUNK_TITLE.match(n):
        return False
    if FRAGMENT_WORDS.match(n):
        return False
    if n.lower() in GENERIC_HEADER:
        return False
    if 'region' in n.lower() or ':' in n:
        return False
    if n.endswith(('.', ',', ';')):
        return False
    if sum(c.isdigit() for c in n) > 2:
        return False
    words = n.split()
    if not (1 <= len(words) <= 7):
        return False
    if n[0].islower():
        return False
    if len(words) >= 4 and SENTENCE_HINT.search(n):
        return False
    # reject mid-sentence captures: a recipe title rarely has 'and'/'with' as first word
    if words[0].lower() in ('and', 'with', 'or', 'but', 'plus'):
        return False
    # truncated titles ending in a connector ('Branzino with', 'Salad of')
    if words[-1].lower() in ('with', 'and', 'of', 'in', 'on', 'for', 'the', 'a', 'an', '&', 'de', 'al'):
        return False
    # generic one/two-word non-dishes
    if n.lower() in ('basic recipes', 'parmesan cheese', 'olive oil', 'sources', 'equipment',
                     'ingredients', 'techniques', 'glossary', 'menus', 'index',
                     'extra-virgin olive oil', 'tomatoes', 'spaghetti', 'mandarin'):
        return False
    # embedded step numbers ('Basil water 1 Pluck the basil leaves')
    if re.search(r'\s\d\s', n):
        return False
    return True

def main():
    recs = json.load(open(f'{BASE}/data/recipes.json'))
    print(f"input: {len(recs)}")
    kept, dropped = [], 0
    for r in recs:
        if not good_title(r['name']):
            dropped += 1
            continue
        if len(r.get('ingredients', [])) < 3 or len(r.get('method', [])) < 1:
            dropped += 1
            continue
        if not r.get('linked_ingredients'):
            dropped += 1
            continue
        r['cuisine'] = classify(r)
        kept.append(r)
    print(f"dropped junk: {dropped}   kept: {len(kept)}")
    print("\nby cuisine (reclassified):")
    for c, n in Counter(x['cuisine'] for x in kept).most_common():
        print(f"  {c:18s} {n}")
    for path in (f'{BASE}/data/recipes.json', f'{BASE}/public/recipes.json',
                 f'{BASE}/skill/flavourlab/data/recipes.json'):
        json.dump(kept, open(path, 'w'), ensure_ascii=False, indent=1)
    print(f"\nSaved → recipes.json (+ public, skill mirrors)")

if __name__ == '__main__':
    main()
