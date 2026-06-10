#!/usr/bin/env python3
"""
Extract the complete pairing list from the flavor-thesaurus EPUB (US edition).
Every entry paragraph starts with 'A & B' (either a full entry or a cross-ref).
Two passes:
  1. collect the flavor-name lexicon = set of all first-names in 'A & ...'
  2. for each 'A & rest' paragraph, find the longest lexicon name prefixing rest → B
Captures pair names only (factual pairing list, no prose).
Output: data/thesaurus_pairings.json (merged with the PDF extraction)
"""
import zipfile, re, json, warnings
from bs4 import BeautifulSoup
warnings.filterwarnings("ignore")

EPUB = ("/Users/usuario/Downloads/The flavor thesaurus - a compendium of pairings, recipes, -- "
        "Niki Segnit -- 1st U_S_ ed, New York, 2010 -- Bloomsbury Publishing USA -- "
        "isbn13 9781596916043 -- 48c129cfaff273834f835484b608f239 -- Anna’s Archive.epub")
OUT = '/Users/usuario/foodpairing-lab/data/thesaurus_pairings.json'

PAIR_START = re.compile(r"^([A-Z][A-Za-z'’]+(?:\s[A-Z][A-Za-z'’]+){0,2})\s*&\s*(.+)$")

def get_paras():
    z = zipfile.ZipFile(EPUB)
    htmls = sorted(n for n in z.namelist() if n.lower().endswith(('.html', '.xhtml', '.htm')))
    paras = []
    for hf in htmls:
        soup = BeautifulSoup(z.read(hf).decode('utf-8', 'ignore'), 'lxml')
        for p in soup.find_all('p'):
            t = p.get_text(' ', strip=True)
            if t:
                paras.append(re.sub(r'[’]', "'", t))
    return paras

def main():
    paras = get_paras()
    print(f"paragraphs: {len(paras)}")

    # pass 1: lexicon of flavor names = all first-names of 'A & ...' lines
    lexicon = set()
    for t in paras:
        m = PAIR_START.match(t)
        if m:
            lexicon.add(m.group(1))
    print(f"lexicon (first names): {len(lexicon)}")

    # pass 2: resolve B by longest lexicon-name prefix of the remainder
    names_by_len = sorted(lexicon, key=len, reverse=True)
    pairs = set()
    unresolved = 0
    for t in paras:
        m = PAIR_START.match(t)
        if not m:
            continue
        a, rest = m.group(1), m.group(2)
        b = next((n for n in names_by_len
                  if rest.startswith(n) and
                  (len(rest) == len(n) or not rest[len(n)].isalpha())), None)
        if b and a != b:
            pairs.add(tuple(sorted((a.lower(), b.lower()))))
        elif not b:
            unresolved += 1
    print(f"pairs from EPUB: {len(pairs)}   (unresolved heads: {unresolved})")

    # merge with existing PDF-derived data
    try:
        old = json.load(open(OUT))
        before = len(pairs)
        for p in old.get('pairs', []):
            pairs.add(tuple(sorted((p[0], p[1]))))
        print(f"merged with PDF set: +{len(pairs) - before} → {len(pairs)} total")
    except Exception:
        pass

    pairs = sorted(pairs)
    ingredients = sorted({x for p in pairs for x in p})
    print(f"TOTAL pairs: {len(pairs)}  ·  ingredients: {len(ingredients)}")
    json.dump({'pairs': [list(p) for p in pairs], 'ingredients': ingredients},
              open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"Saved → {OUT}")

if __name__ == '__main__':
    main()
