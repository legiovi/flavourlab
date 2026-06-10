#!/usr/bin/env python3
"""
Extract the full pairing dataset from the foodpairing reference book.
Two sources per ingredient chapter (pages 40-371):
  1. Named pairings:  'Classic pairing: X and Y', 'Potential pairing: ...',
     "Chef's pairing: ...", 'Classic dish/drink/recipe: ...'
  2. Pairing-grid row labels: the ingredient names listed in the
     'Ingredient pairings with X' dot-matrix grids.
Output: data/book_pairings.json  { chapter: {named:[...], grid:[...]} }
"""
import pdfplumber, re, json, sys, warnings
warnings.filterwarnings("ignore")

PDF = '/Users/usuario/Documents/06_Libros/Cocina/The_Art_and_Science_of_Foodpairing_10,000_flavour_matches_Peter.pdf'
OUT = '/Users/usuario/foodpairing-lab/data/book_pairings.json'

# Chapter list from the book TOC (page → chapter name)
CHAPTERS = {
    40:"Kiwi",44:"Apple",50:"Celeriac",54:"Vanilla",58:"Chocolate",64:"Cauliflower",
    68:"Strawberry",72:"Basil",76:"Watermelon",80:"Tequila",84:"Lemon & Lime",
    90:"Chilli Pepper",96:"Coriander",100:"Fish",106:"Red Bell Pepper",110:"Garlic",
    116:"Sweet Potato",120:"Cognac",124:"Shiitake Mushroom",128:"Cinnamon",132:"Coconut",
    136:"Makrut Lime",138:"Pilsner",140:"Ginger",144:"Lemongrass",148:"Crustaceans",
    154:"Sauvignon Blanc",158:"Tomato",162:"Blue Cheese",166:"Butternut Squash",
    168:"Olive Oil",174:"Sourdough Rye Bread",178:"Lambic Beer",180:"Meat",190:"Truffle",
    194:"French Fries",198:"Goats' Cheese",202:"Blueberry",206:"Apricot",
    208:"Jasmine Blossom",212:"Gin",216:"Black Olive",218:"Bergamot",220:"Beetroot",
    226:"Pomegranate",228:"Cumin",230:"Carrot",234:"Orange",238:"Rum",240:"Pineapple",
    244:"Doenjang",248:"Cassava",252:"Plantain",254:"Cardamom",258:"Peach",262:"Yogurt",
    264:"Seaweed",268:"Cucumber",270:"Black Peppercorns",276:"Iberico Ham",
    280:"Parmigiano-Reggiano",284:"Cabernet Sauvignon",286:"Chorizo",290:"Bourbon Whiskey",
    292:"Durian",294:"Coffee",298:"Soy Sauce",302:"Kimchi",306:"Sesame Seeds",310:"Mango",
    314:"Balsamic Vinegar",318:"Green Beans",322:"Durum Pasta",326:"Artichoke",
    330:"Hazelnut",334:"Brie",338:"Raspberry",340:"Banana",344:"Almond",348:"Pear",
    352:"Avocado",356:"Grapefruit",360:"Tea",366:"Elderflower Blossom",368:"Oyster",
}

NAMED_RE = re.compile(
    r"(?:Classic|Potential|Chef'?s?)\s+(?:pairing|dish|drink|recipe|combination)s?:\s*([^\n]{4,90})",
    re.I)

# split 'X and Y' / 'X, Y and Z' partner phrases
def parse_partners(phrase, chapter):
    phrase = phrase.strip().rstrip('.')
    parts = re.split(r'\s*(?:,|and|with|&)\s+', phrase)
    chap_low = chapter.lower().split()[0]
    out = []
    for p in parts:
        p = p.strip(' -–—')
        if not (2 < len(p) < 45):
            continue
        if chap_low in p.lower():
            continue  # skip the chapter ingredient itself
        if re.search(r'\d', p):
            continue
        out.append(p)
    return out

# grid row labels: short food-name lines on grid pages
JUNK_LINE = re.compile(
    r'^(ingredient pairings|classic|potential|chef|the |a |in |for |when |this |it |'
    r'page|see |aroma|profile|key|fig\.|\W)', re.I)

def grid_labels(text, chapter):
    labels = []
    chap_low = chapter.lower().split()[0]
    for line in text.split('\n'):
        l = line.strip()
        # strip leading bullet/dot noise
        l = re.sub(r'^[•·\.\s]+', '', l)
        l = re.sub(r'[•·]+', '|', l)
        for piece in l.split('|'):
            p = piece.strip(' -–—.')
            if not (3 < len(p) < 42):
                continue
            if JUNK_LINE.match(p):
                continue
            if re.search(r'\d', p):
                continue
            # food names: mostly lowercase words, 1-4 words, letters/space/hyphen/apostrophe only
            if not re.fullmatch(r"[A-Za-zÀ-ÿ' \-]+", p):
                continue
            words = p.split()
            if len(words) > 5:
                continue
            # reject lines that look like prose fragments (contain common stopwords mid-line)
            if any(w.lower() in ('the','is','are','was','of','to','that','which','their') for w in words):
                continue
            if chap_low in p.lower():
                continue
            # mostly-lowercase heuristic: grid labels are lowercase in the book
            lower_ratio = sum(1 for c in p if c.islower()) / max(1, sum(1 for c in p if c.isalpha()))
            if lower_ratio < 0.6:
                continue
            labels.append(p.lower())
    return labels

def main():
    pages = sorted(CHAPTERS.keys())
    result = {}
    with pdfplumber.open(PDF) as pdf:
        for idx, start in enumerate(pages):
            chapter = CHAPTERS[start]
            end = pages[idx + 1] if idx + 1 < len(pages) else 372
            named, grid = [], []
            for p in range(start, end):
                try:
                    text = pdf.pages[p - 1].extract_text() or ''
                except Exception:
                    continue
                for m in NAMED_RE.finditer(text):
                    named.extend(parse_partners(m.group(1), chapter))
                if 'pairings with' in text.lower() or '•' in text:
                    grid.extend(grid_labels(text, chapter))
            # dedupe, keep order
            def dedupe(seq):
                seen, out = set(), []
                for x in seq:
                    k = x.lower()
                    if k not in seen:
                        seen.add(k); out.append(x)
                return out
            result[chapter] = {'named': dedupe(named), 'grid': dedupe(grid)}
            print(f"{chapter:22s} named={len(result[chapter]['named']):3d} grid={len(result[chapter]['grid']):3d}")
    total_named = sum(len(v['named']) for v in result.values())
    total_grid = sum(len(v['grid']) for v in result.values())
    print(f"\nTOTAL named pairings: {total_named}")
    print(f"TOTAL grid pairings:  {total_grid}")
    print(f"GRAND TOTAL:          {total_named + total_grid}")
    json.dump(result, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"Saved → {OUT}")

if __name__ == '__main__':
    main()
