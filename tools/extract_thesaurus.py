#!/usr/bin/env python3
"""
Extract pairings from the flavour-thesaurus reference (408-page OCR PDF).
Entry headings were lost in OCR, but every pairing appears in cross-reference
lines ('X & Y: See Y & X, page N') and inline 'See also X & Y, page N' refs.
Output: data/thesaurus_pairings.json  {"pairs": [[a, b], ...], "ingredients": [...]}
"""
import pdfplumber, re, json, warnings
warnings.filterwarnings("ignore")

PDF = ('/Users/usuario/Downloads/The flavour thesaurus - pairings, recipes and ideas for the -- '
       'Segnit, Niki -- Bloomsbury UK (Trade), London, 2010 -- London ; New York - Bloomsbury -- '
       'isbn13 9780747599777 -- ebd826c5faed67dae0a9deabf046bd0f -- Anna’s Archive.pdf')
OUT = '/Users/usuario/foodpairing-lab/data/thesaurus_pairings.json'

NAME = r"[A-Z][A-Za-z'’]+(?:\s[A-Za-z'’]+){0,2}"
CROSS = re.compile(rf'({NAME})\s*&\s*({NAME})\s*[:;,]?\s*[Ss]ee\b')
INLINE = re.compile(rf'[Ss]ee\s+(?:also\s+)?({NAME})\s*&\s*({NAME})\s*,?\s*page')

STOP = {'see', 'also', 'page', 'the', 'and', 'with', 'for', 'this', 'that', 'chapter'}

def clean(n):
    n = re.sub(r"[’']", "'", n).strip()
    n = re.sub(r'\s+', ' ', n)
    if not (2 < len(n) < 28):
        return None
    words = n.split()
    if any(w.lower() in STOP for w in words):
        return None
    if len(words) > 3:
        return None
    return n.lower()

def main():
    pairs = set()
    with pdfplumber.open(PDF) as pdf:
        total = len(pdf.pages)
        for i in range(total):
            try:
                t = pdf.pages[i].extract_text() or ''
            except Exception:
                continue
            for rx in (CROSS, INLINE):
                for m in rx.finditer(t):
                    a, b = clean(m.group(1)), clean(m.group(2))
                    if a and b and a != b:
                        pairs.add(tuple(sorted((a, b))))
            if (i + 1) % 100 == 0:
                print(f"  page {i+1}/{total}  pairs so far: {len(pairs)}")
    pairs = sorted(pairs)
    ingredients = sorted({x for p in pairs for x in p})
    print(f"\nUnique pairings: {len(pairs)}")
    print(f"Unique ingredients: {len(ingredients)}")
    print("Sample:", pairs[:12])
    json.dump({'pairs': [list(p) for p in pairs], 'ingredients': ingredients},
              open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"Saved → {OUT}")

if __name__ == '__main__':
    main()
