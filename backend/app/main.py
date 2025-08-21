# main.py
# ------------------------------------------------------------
# FastAPI-Backend:
# - /predict: Bild empfangen, YOLO-Inferenz ausführen, Nährwerte pro 100 g
#             für jedes erkannte Label via OpenFoodFacts anreichern.
#             Erzeugt image_id und sha256, speichert Bild temporär.
# - /healthz: Einfacher Healthcheck (Status)
# - /labels:  Modell-Labels ausgeben (für Feedback-Dropdown).
# - /model-info: Modellnamen an Frontend melden.
# - /feedback: Nutzerfeedback in JSON-Datei anhängen.
#              Verschiebt Bild bei vorhandenem image_id von tmp -> uploads.
# ------------------------------------------------------------

from fastapi import FastAPI, UploadFile, File, Request                  # Webframework & Upload-Handling & Feedback-Endpoint (JSON-Body)
from fastapi.middleware.cors import CORSMiddleware                      # CORS-Header erlauben Cross-Origin-Frontend
from datetime import datetime
from zoneinfo import ZoneInfo
# import json
import hashlib, uuid, os, json, shutil, time                            # UUIDs für Feedback-IDs, Hashing, Dateizugriff, Dateimanagement, Temp-Cleanup
from pathlib import Path
from yolo_predict import run_inference, get_model_name                  # eigene Inferenz & Modellinfo
from openfoodfacts_client import get_nutrition_bulk                     # Batch-Funktion: Labels -> Nährwerte

app = FastAPI()                                                         # FastAPI-App anlegen

# --- CORS für Frontend-Zugriff ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                                                # später evtl. einschränken auf Frontend-URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zentrale Pfade (relativ zum Backend-Verzeichnis)
BACKEND_ROOT = Path("/home/ec2-user/food-detector-app/backend")         # Root-Verzeichnis des Backends
TMP_DIR      = BACKEND_ROOT / "tmp_uploads"                             # Temporäres Upload-Verzeichnis
UPLOAD_DIR   = BACKEND_ROOT / "uploads"                                 # Upload-Verzeichnis
FEEDBACK_DIR = BACKEND_ROOT / "feedback"                                # Feedback-Verzeichnis
FEEDBACK_FILE = FEEDBACK_DIR / "feedback.json"                          # Feedback-Datei
TMP_DIR.mkdir(parents=True, exist_ok=True)                              # Verzeichnisse anlegen, falls nicht vorhanden
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
if not FEEDBACK_FILE.exists():                                          # Feedback-Datei anlegen, falls nicht vorhanden
    FEEDBACK_FILE.write_text("[]", encoding="utf-8")                    # Leeres JSON-Array

# ------------------------------------------------------------
# Einfacher Aufräumer für temporäre Uploads (älter als X Stunden)
# Kann bei jedem /predict kurz laufen (kostet wenig)
# ------------------------------------------------------------
def cleanup_tmp(max_age_hours: int = 24) -> None:                       # Aufräumen nach max_age_hours = 24h
    now = time.time()
    threshold = max_age_hours * 3600
    try:
        for p in TMP_DIR.glob("*.jpg"):
            if now - p.stat().st_mtime > threshold:
                p.unlink(missing_ok=True)
    except Exception:
        # bewusst stilles Aufräumen
        pass

# ------------------------------------------------------------
# /healthz
# - Liefert einfachen Healthcheck
# ------------------------------------------------------------
@app.get("/healthz") 
async def healthz():
    return {"status": "ok"}


# ------------------------------------------------------------
# /model-info
# - Liefert nur den Modellnamen (Anzeige im Frontend-Header)
# ------------------------------------------------------------
@app.get("/model-info") 
async def get_model_info():
    return {"model": get_model_name()}


# ------------------------------------------------------------
# /labels
# - Liefert alle vom Modell erkennbaren Klassen (für Feedback-Dropdown)
# ------------------------------------------------------------
@app.get("/labels")
async def get_labels():
    # Zugriff auf das YOLO-Modell-Objekt (names -> {class_id: "label"})
    from yolo_predict import model
    return {"labels": list(model.names.values())}


# ------------------------------------------------------------
# /predict
# - Nimmt ein Bild entgegen (multipart/form-data)
# - Führt YOLO aus
# - Fragt für jedes erkannte Label die Nährwerte (pro 100 g) bei OFF ab
# - Mischt Nährwerte in jedes Prediction-Item unter "nutrition_per_100g"
# - Erzeugt image_id (UUID) + sha256, speichert Bild TEMPORÄR in tmp_uploads
#         und gibt image_id/sha256 im JSON an das Frontend zurück.
# ------------------------------------------------------------
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # Temp-Cleanup bei jedem Request
    cleanup_tmp(24)

    # 1) Gesamte Datei in Bytes lesen (für PIL/YOLO)
    image_bytes = await file.read()
    
    # IDs bilden (für Uploads)
    image_id = uuid.uuid4().hex                          # UUID als eindeutige ID
    sha256 = hashlib.sha256(image_bytes).hexdigest()     # SHA256-Hash des Bildes (64-stellig)
    
    # Originalbild temporär speichern – ohne Original-Dateinamen:
    tmp_path = TMP_DIR / f"{image_id}.jpg"
    with open(tmp_path, "wb") as f:
        f.write(image_bytes)
    tmp_path.touch()  # mtime aktualisieren (hilft später beim Aufräumen)
    # Originalbild dauerhaft speichern
    # with open(UPLOAD_DIR / f"{image_id}.jpg", "wb") as f:
    #     f.write(image_bytes)

    # 2) YOLO-Inferenz durchführen -> {"predictions": [ { label, confidence, ... }, ... ]}
    result = run_inference(image_bytes)
    predictions = result.get("predictions", [])

    # 3) Alle Label-Namen einsammeln (nur die, die vorhanden sind)
    labels = []
    for p in predictions:
        lbl = (p.get("label") or "").strip()
        if lbl:
            labels.append(lbl)

    # 4) Nährwertdaten in einem Rutsch holen (lru_cache im Client verhindert Doppelanfragen)
    #    Rückgabe-Form: { "<label in lowercase>": { ...naehrwerte... } | None }
    nutrition_map = get_nutrition_bulk(labels)

    # 5) Predictions anreichern: Für jedes Item die passenden Nährwerte dranhängen
    enriched_items = []
    for p in predictions:
        key = (p.get("label") or "").strip().lower()
        enriched_items.append({
            **p,  # behält class_id, label, confidence, ggf. bbox
            "nutrition_per_100g": nutrition_map.get(key)  # kann None sein, wenn OFF nichts Passendes hat
        })

    # 6) Antwortschema, wie Frontend es nutzt:
    #    App.jsx erwartet { "items": [...] }
    return {"items": enriched_items,    # erkannte Objekte
            "image_id": image_id,       # eindeutige ID für das Bild
            "sha256": sha256,           # SHA256-Hash des Bildes
            "storage": "temp"           # Speicherort des Bildes (Info für Debugging)
           }


# ------------------------------------------------------------
# /feedback
# - Hängt Feedback-Objekte an eine JSON-Datei an (einfaches Logging)
# - Erwartet JSON-Body mit 4 Feldern
#   1. original: Der ursprüngliche Text
#   2. correction: Der korrigierte Text
#   3. confidence: Die Konfidenz des Modells (0-100)
#   4. image_id: Die ID des Bildes
# - Wenn eine image_id übergeben wurde und die Datei noch in tmp liegt,
#   wird sie nach uploads verschoben (dauerhafte Ablage).
# ------------------------------------------------------------
@app.post("/feedback")
async def receive_feedback(request: Request):
    try:
        data = await request.json()                                 # JSON-Body einlesen
        print("DEBUG FEEDBACK:", data)

        # Filesystem-Aktion: tmp → uploads (falls vorhanden)
        image_id = data.get("4. image_id") or data.get("image_id")
        if image_id:
            tmp_file  = TMP_DIR   / f"{image_id}.jpg"
            perm_file = UPLOAD_DIR / f"{image_id}.jpg"
            if tmp_file.exists():
                try:
                    shutil.move(str(tmp_file), str(perm_file))
                except Exception as move_err:
                    print("⚠️ Konnte tmp-Datei nicht verschieben:", move_err)       

        # Zeitstempel (Europa/Berlin), plus die 4 Felder aus dem Frontend
        feedback_entry = {
            "timestamp": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d %H:%M:%S %z"),
            "original": data.get("1. original"),
            "correction": data.get("2. correction"),
            "confidence": data.get("3. confidence"),
            "image_id": image_id,
            "sha256": data.get("5. sha256", "unbekannt"),           # SHA256-Hash des Bildes
        }

        # Datei vorbereiten, falls sie noch nicht existiert
        if not os.path.exists(FEEDBACK_FILE):
            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

        # Vorhandenen Inhalt laden
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                feedback_data = json.load(f)
            if not isinstance(feedback_data, list):
                feedback_data = []                                  # Sicherstellen, dass es eine Liste ist
        except Exception:
            feedback_data = []                                      # Bei Fehlern ebenfalls leere Liste

        # Neuen Eintrag anhängen
        feedback_data.append(feedback_entry)

        # und zurückschreiben
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        return {"status": "ok", "entry": feedback_entry}

    except Exception as e:
        print("⚠️ Fehler beim Einlesen des Feedback-Requests:", e)
        return {"status": "error", "message": str(e)}
