#!/usr/bin/env python3
"""
PDF recipe extractor v2 for FlavourLab.
- Full page range (no 400-page cap)
- Better title detection (scans more lines, filters page furniture)
- Multi-page method capture
- English-only output
"""
import pdfplumber, os, re, json, sys, warnings
warnings.filterwarnings("ignore")

BOOKS_DIR = '/Users/usuario/Documents/06_Libros/Cocina/'
OUT = '/Users/usuario/foodpairing-lab/data/recipes_pdf.json'

UNIT_SIGNALS = ['g ', 'ml ', 'oz ', 'cup', 'tbsp', 'tsp', 'kg', 'litre', 'liter',
                'pound', 'lb', 'bunch', 'clove', 'pinch', 'handful', 'sprig', 'knob']
SERV_RE = re.compile(r'\b(serves|makes|yields?|for \d+\s*(people|persons|servings))\b', re.I)
STEP_RE = re.compile(r'(?:^|\n)\s*(\d{1,2})[.\)]\s+([A-Z][^\n]{25,400})', re.M)
PARA_RE = re.compile(r'([A-Z][^.!?]{40,400}[.!?])')

EN_WORDS = set("the and with of to in for until add then over heat oil salt pepper "
               "water cook minutes pan large medium small remove from into serve".split())

SKIP_TITLE = re.compile(
    r'^(serves|makes|yields?|page|index|contents|chapter|introduction|note|tip|'
    r'preparation|ingredients?|method|for the|copyright|acknowledg|glossary|about)',
    re.I)


def is_english(text):
    words = re.findall(r'\b[a-z]+\b', text.lower())[:150]
    return sum(1 for w in words if w in EN_WORDS) >= 4


def looks_title(line):
    line = line.strip()
    if not (4 < len(line) < 70):
        return False
    if not line[0].isupper() or line[0].isdigit():
        return False
    if SKIP_TITLE.match(line):
        return False
    if sum(c.isdigit() for c in line) > 3:
        return False
    # avoid lines that are clearly sentences
    if line.endswith(('.', ',', ';', ':')) and len(line) > 40:
        return False
    return True


def extract_pdf(path, cuisine, book_id, max_pages=900):
    recs = []
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:
        print(f"  !open fail: {e}", file=sys.stderr)
        return recs
    total = min(len(pdf.pages), max_pages)
    i = 0
    while i < total:
        try:
            text = pdf.pages[i].extract_text() or ''
        except Exception:
            i += 1
            continue
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) < 5:
            i += 1
            continue
        # candidate titles in the first 10 lines
        for j, line in enumerate(lines[:10]):
            if not looks_title(line):
                continue
            rest = '\n'.join(lines[j + 1:j + 30])
            sig = sum(1 for s in UNIT_SIGNALS if s in rest.lower())
            if sig < 2:
                continue
            # gather ingredient-ish lines
            ings = []
            for il in lines[j + 1:j + 32]:
                ill = il.lower()
                if any(s in ill for s in UNIT_SIGNALS) or (il[:1].isdigit() and len(il) > 6):
                    if len(il) < 150:
                        ings.append(il)
            if len(ings) < 3:
                continue
            # servings
            serv = ''
            m = SERV_RE.search(text)
            if m:
                line_with = next((l for l in lines if m.group(0).lower() in l.lower()), '')
                if len(line_with) < 60:
                    serv = line_with
            # method: numbered steps on this page + next two pages
            method = []
            blob = text
            for k in (1, 2):
                if i + k < total:
                    try:
                        blob += '\n' + (pdf.pages[i + k].extract_text() or '')
                    except Exception:
                        pass
            steps = STEP_RE.findall(blob)
            if steps:
                method = [s[1].strip() for s in steps[:10]]
            else:
                # fall back: long sentence paragraphs after the ingredient zone
                tail = blob[blob.find(ings[-1]) + len(ings[-1]):] if ings[-1] in blob else blob
                paras = PARA_RE.findall(tail)
                method = [p.strip() for p in paras[:6] if len(p) > 60]
            if not method:
                continue
            full = line + ' ' + ' '.join(ings) + ' ' + ' '.join(method)
            if not is_english(full):
                continue
            recs.append({
                'id': f"{book_id}_{len(recs) + 1}",
                'name': line.title() if line.isupper() else line,
                'cuisine': cuisine,
                'servings': serv,
                'description': '',
                'ingredients': [re.sub(r'\s+', ' ', x)[:140] for x in ings[:18]],
                'method': [re.sub(r'\s+', ' ', m)[:450] for m in method[:10]],
                'source': 'pdf',
            })
            break  # one recipe anchor per page
        i += 1
    pdf.close()
    return recs


BOOKS = [
    ("Big_Mamma_Italian_Recipes_30min.pdf", "Italian", "p_bigmamma"),
    ("Mexico_the_cookbook_Carrillo_Arronte,_Margarita,_author_2014_London.pdf", "Mexican", "p_mexico"),
    ("Faviken_Magnus_Nilsson_First_Edition,_2012_Phaidon_Press_9780714864709.pdf", "Nordic", "p_faviken"),
    ("Bibo_Recipes_Dani_Garcia_2018_Dani_Garcia_Books_daae53ee2932f2f.pdf", "Spanish", "p_bibo"),
    ("Bachour_Gastro_Antonio_Bachour_2020_Vilbo_9788412131437_30216ce.pdf", "Pastry", "p_bachour"),
    ("Disfrutar_Catalogue_2014_2017_1_Oriol_Castro,_Eduard_Xatruch,_Mateu.pdf", "Spanish Avant-Garde", "p_disfrutar"),
    ("A_book_of_Middle_Eastern_food_Roden,_Claudia;_Parkins,_Alta_Ann.pdf", "Middle Eastern", "p_mideast"),
    ("Bread_A_Baker's_Book_of_Techniques_and_Recipes_Jeffrey_Hamelman.pdf", "Baking", "p_bread"),
    ("Roots_Essential_Catalan_Cuisine_According_to_El_Celler_de_Joan_Roca.pdf", "Catalan", "p_catalan"),
    ("Felicidad_Carme_Ruscalleda_i_Serra_2018_Planeta_Gastro_9788408194262.pdf", "Catalan", "p_felicidad"),
    ("The_Arabesque_table_contemporary_recipes_from_the_Arab_Kassis,_Reem.pdf", "Middle Eastern", "p_arabesque"),
    ("Thai_Food_David_Thompson_2002_Random_House_Digital,_Inc_9781580084628.pdf", "Thai", "p_thai"),
    ("BAO_The_Cookbook_Erchen_Chang,_Shing_Tat_Chung,_Wai_Ting_Chung_2023.pdf", "Asian", "p_bao"),
    ("Chicken_and_Charcoal_yardbird.pdf", "Asian", "p_yakitori"),
    ("lebanese cuisine.pdf", "Middle Eastern", "p_lebanese"),
    ("mezze.pdf", "Middle Eastern", "p_mezze"),
    ("Garde_Manger_The_Art_and_Craft_of_the_Cold_Kitchen_The_Culinary.pdf", "Garde Manger", "p_gardemanger"),
    ("Le_Cordon_Bleu_Patisserie_and_Baking_Foundations_by_The_Chefs_of.pdf", "Pastry", "p_cordonbleu"),
    ("Cooking Sous Vide, Under Pressure by Thomas Keller.pdf", "Modern French", "p_sousvide"),
    ("Ducasse_Flavors_of_France_Linda_Dannenberg,_Alain_Ducasse_1,_1998.pdf", "French", "p_ducasse"),
    ("White_heat_White,_Marco_Pierre,_author;_Clarke,_Bob_Carlos,_1950.pdf", "French", "p_whiteheat"),
    ("Core_Clare_Smyth_2022_Phaidon_Press_9781838664060_02f790aa01933.pdf", "British", "p_core"),
    ("Rogan the cookbook -- Simon Rogan [Rogan, Simon] -- Place of publication not identified, 2018 -- Harpercollins Publishers Limited -- 9780008232726 -- b4c3f6eb4566c9cef0deb2922afcabe3 -- Anna’s Archive.pdf", "British", "p_rogan"),
    ("OPSO- A Modern Greek Cookbook -- Nikos Roussos, Andreas Labridis -- 2024 -- Ebury Press -- 9781529944136 -- 823ba0148bb1dc51663cf030e4236db7 -- Anna’s Archive.pdf", "Greek", "p_greek"),
    ("Scook_The_Complete_Cookery_Guide_Anne_Sophie_Pic_2015_Jacqui_Small.pdf", "French", "p_scook"),
    ("Míchel brass essential cuisine.pdf", "French", "p_bras"),
    ("Manresa_An_Edible_Reflection_David_Kinch,_Christine_Muhlke,_Eric.mobi", "Californian", "p_manresa"),
]


def main():
    all_recipes, seen = [], set()
    for fname, cuisine, book_id in BOOKS:
        path = BOOKS_DIR + fname
        if not os.path.exists(path) or fname.endswith('.mobi'):
            print(f"skip: {fname[:45]}")
            continue
        recs = extract_pdf(path, cuisine, book_id)
        kept = 0
        for r in recs:
            k = r['name'].lower().strip()
            if k in seen or len(k) < 4:
                continue
            seen.add(k)
            all_recipes.append(r)
            kept += 1
        print(f"{book_id:16s} {kept:4d} recipes  ·  {fname[:46]}")
    print(f"\nTOTAL: {len(all_recipes)}")
    json.dump(all_recipes, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"Saved → {OUT}")


if __name__ == '__main__':
    main()
