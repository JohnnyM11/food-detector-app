# openfoodfacts_client.py
# ------------------------------------------------------------
# Hilfsfunktionen, um Nährwerte pro 100 g aus der OpenFoodFacts-DB
# für erkannte Lebensmittel (YOLO-Labels) abzurufen.
#
# Design:
# - Keine Übersetzungs-Tabelle (LABEL_MAP): Suche mit dem
#   englischen YOLO-Label und probiere ein paar neutrale Varianten.
# - @lru_cache reduziert wiederholte gleiche Anfragen in einer Session.
# - Robust gegenüber teilweise fehlenden Nährwertfeldern (kJ/kcal).
# - Ergebnis-Format ist Frontend-freundlich.
# ------------------------------------------------------------

from functools import lru_cache            # einfacher In‑Memory‑Cache für Funktionsaufrufe
import requests                            # HTTP‑Client für die OFF‑API
import re                                  # kleine String‑Normalisierung (optional)

# Basis‑URL der "klassischen" OFF‑Such‑API, liefert JSON
OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

# HTTP‑Header für die Anfrage. Ein sinnvoller User‑Agent ist Best Practice:
# - Identifiziert die App (Name/Version)
# - Enthält eine Kontaktmöglichkeit (E‑Mail/URL) für Rückfragen/Rate‑Limits
# OpenFoodFacts hilft es bei Problemen/Fragen und erleichtert die Kontaktaufnahme.
HEADERS = {
    "User-Agent": "Coburg-BA-Naehrwerte/1.0 (mailto:your.email@example.com)"
}


def _normalize_base(label: str) -> str:
    """
    Minimal neutrale Normalisierung:
    - trimmen
    - in Kleinbuchstaben
    - '_' und '-' werden zu Leerzeichen
    - Mehrfach‑Leerzeichen reduzieren
    """
    s = (label or "").strip().lower()
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def _query_variants(label: str) -> list[str]:
    """
    Liefert 2–3 harmlose Suchvarianten, um typische Schreibweisen abzudecken,
    ohne die Bedeutung zu verändern (z. B. 'hotdog' vs. 'hot dog').
    Keine Übersetzung/Internationalisierung — nur Schreibvarianten.
    """
    base = _normalize_base(label)           # z. B. "hotdog"
    spaced = re.sub(r"(?<=\D)(?=\d)|(?<=\d)(?=\D)", " ", base)  # trenne Zahl/Buchstabe (z. B. "7up" -> "7 up")
    # Wenn der String keine Leerzeichen enthält, erzeuge eine Variante mit einem eingefügten Space
    # (heuristisch: vor dem letzten 3er‑Chunk, z. B. "hotdog" -> "hot dog").
    if " " not in base and len(base) >= 6:
        split_var = base[:-3] + " " + base[-3:]
        variants = [base, spaced, split_var]
    else:
        variants = [base, spaced]

    # Deduplizieren bei identischen Varianten
    seen = set()
    out = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


@lru_cache(maxsize=256)
def get_nutrition_for_food(query: str) -> dict | None:
    """
    Fragt OpenFoodFacts nach Nährwerten pro 100 g für einen Suchbegriff.
    Rückgabe:
      {
        "query": "<finaler Suchbegriff>",
        "product_name": "...",
        "energy_kj":  ... | None,
        "energy_kcal": ... | None,
        "fat_g":      ... | None,
        "carbs_g":    ... | None,
        "sugars_g":   ... | None,
        "protein_g":  ... | None,
        "source":     "OpenFoodFacts"
      }
    oder None, wenn nichts Brauchbares gefunden wurde.
    """
    # mehrere neutrale Varianten ausprobieren (z. B. "hotdog" und "hot dog")
    candidates = _query_variants(query)

    # wir iterieren über Varianten und nehmen den ersten brauchbaren Treffer
    for q in candidates:
        params = {
            "search_terms": q,                   # Volltext‑Suche
            "search_simple": 1,                  # einfache Suche aktivieren
            "action": "process",                 # API‑Parameter laut OFF
            "page_size": 8,                      # kleine Trefferliste reicht, spart Bandbreite
            "json": 1,                           # JSON‑Antwort
            "fields": "product_name,lang,nutriments,categories_tags"  # nur relevante Felder
        }
        try:
            r = requests.get(OFF_SEARCH_URL, params=params, headers=HEADERS, timeout=8)
            r.raise_for_status()
            data = r.json()
        except Exception:
            # Netzwerk-/Parsing‑Fehler -> nächste Variante testen
            continue

        products = (data or {}).get("products", []) or []
        if not products:
            # keine Treffer -> nächste Variante
            continue

        # Scoring: wähle den "besten" Kandidaten
        # Idee:
        #   1) Mehr Nährwertfelder => besser
        #   2) Sprache de/en leicht bevorzugen
        #   3) "Generische" Kategorien leicht bevorzugen (nicht zwingend notwendig, hilft aber)
        def completeness_score(p) -> int:
            n = p.get("nutriments") or {}
            keys = ["energy-kj_100g", "energy_100g", "energy-kcal_100g", "fat_100g",
                    "carbohydrates_100g", "sugars_100g", "proteins_100g"]
            return sum(1 for k in keys if n.get(k) is not None)

        def lang_score(p) -> int:
            lang = (p.get("lang") or "").lower()
            return 2 if lang in {"de", "en"} else 0

        def generic_score(p) -> int:
            cats = p.get("categories_tags") or []
            # sehr grobe Heuristik: "fruits", "vegetables", "generic"
            tag_hits = any(("en:generic" in c) or ("en:fruits" in c) or ("en:vegetables" in c) or ("de:obst" in c) or ("de:gemuese" in c)
                           for c in cats)
            return 1 if tag_hits else 0

        def total_score(p) -> tuple:
            # sort() benutzt tuple‑Vergleich, daher zuerst "completeness", dann "lang", dann "generic"
            return (completeness_score(p), lang_score(p), generic_score(p))

        products.sort(key=total_score, reverse=True)

        # nun durch die (jetzt sortierten) Produkte gehen und den ersten brauchbaren Datensatz zurückgeben
        for p in products:
            n = p.get("nutriments") or {}

            # Mögliche OFF‑Keys (pro 100 g)
            kj   = n.get("energy-kj_100g") or n.get("energy_100g")  # manche Einträge benutzen energy_100g
            kcal = n.get("energy-kcal_100g")
            fat  = n.get("fat_100g")
            carbs = n.get("carbohydrates_100g")
            sugars = n.get("sugars_100g")
            protein = n.get("proteins_100g")

            # Falls nur eines von kJ/kcal vorhanden ist, rechne um (1 kcal = 4.184 kJ)
            if kj is None and kcal is not None:
                try:
                    kj = round(float(kcal) * 4.184, 1)
                except Exception:
                    kj = None
            if kcal is None and kj is not None:
                try:
                    kcal = round(float(kj) / 4.184, 1)
                except Exception:
                    kcal = None

            # Wenn gar nichts Sinnvolles da ist, nächstes Produkt
            if all(v is None for v in [kj, kcal, fat, carbs, sugars, protein]):
                continue

            # Helfer zum sicheren Runden/Konvertieren
            def _r(x):
                try:
                    return round(float(x), 1)
                except Exception:
                    return None

            return {
                "query": q,                                # tatsächlich verwendeter Suchstring
                "product_name": p.get("product_name"),     # OFF‑Produktname (kann None sein)
                "energy_kj": _r(kj),
                "energy_kcal": _r(kcal),
                "fat_g": _r(fat),
                "carbs_g": _r(carbs),
                "sugars_g": _r(sugars),
                "protein_g": _r(protein),
                "source": "OpenFoodFacts"
            }

    # Keine Variante hat brauchbare Daten geliefert
    return None


def get_nutrition_bulk(labels: list[str]) -> dict[str, dict | None]:
    """
    Batch‑Abfrage für mehrere Labels. Benutzt automatisch den Cache der Einzel‑Funktion.
    Rückgabe: { "<label in lowercase>": {..Nährwerte..} | None }
    """
    out: dict[str, dict | None] = {}
    seen: set[str] = set()
    for lbl in labels:
        key = (lbl or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out[key] = get_nutrition_for_food(key)
    return out
