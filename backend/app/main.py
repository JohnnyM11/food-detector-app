# main.py
# ------------------------------------------------------------
# FastAPI-Backend:
# - /predict: Bild empfangen, YOLO-Inferenz ausführen, Nährwerte pro 100 g
#             für jedes erkannte Label via OpenFoodFacts anreichern.
# - /labels:  Modell-Labels ausgeben (für Feedback-Dropdown).
# - /model-info: Modellnamen an Frontend melden.
# - /feedback: Nutzerfeedback in JSON-Datei anhängen.
# ------------------------------------------------------------

from fastapi import FastAPI, UploadFile, File, Request                  # Webframework & Upload-Handling & Feedback-Endpoint (JSON-Body)
from fastapi.middleware.cors import CORSMiddleware                      # CORS-Header erlauben Cross-Origin-Frontend
from datetime import datetime
from zoneinfo import ZoneInfo
# import json
import hashlib, uuid, os, json                                          # UUIDs für Feedback-IDs, Dateizugriff
from pathlib import Path
from yolo_predict import run_inference, get_model_name                  # eigene Inferenz & Modellinfo
from openfoodfacts_client import get_nutrition_bulk                     # Batch-Funktion: Labels -> Nährwerte

app = FastAPI()                                                         # FastAPI-App anlegen

UPLOAD_DIR = Path("/home/ec2-user/food-detector-app/backend/uploads")   # Upload-Verzeichnis
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)                           # Verzeichnis anlegen, falls nicht vorhanden

# --- CORS für Frontend-Zugriff ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                                                # später evtl. einschränken auf Frontend-URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# ------------------------------------------------------------
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # 1) Gesamte Datei in Bytes lesen (für PIL/YOLO)
    image_bytes = await file.read()
    
    # Dateinamen-Hash generieren (für Uploads)
    image_id = uuid.uuid4().hex                          # UUID als eindeutige ID
    sha256 = hashlib.sha256(image_bytes).hexdigest()     # SHA256-Hash des Bildes (64-stellig)
    # Originalbild speichern – ohne Original-Dateinamen:
    with open(UPLOAD_DIR / f"{image_id}.jpg", "wb") as f:
        f.write(image_bytes)

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
            "sha256": sha256            # SHA256-Hash des Bildes
           }


# ------------------------------------------------------------
# /feedback
# - Hängt Feedback-Objekte an eine JSON-Datei an (einfaches Logging)
#   Pfad bitte bei Bedarf anpassen (existiert auf deinem Server?)
# ------------------------------------------------------------
FEEDBACK_FILE = Path("/home/ec2-user/food-detector-app/backend/feedback/feedback.json")

@app.post("/feedback")
async def receive_feedback(request: Request):
    try:
        data = await request.json()
        print("DEBUG FEEDBACK:", data)

        # Zeitstempel (Europa/Berlin), plus die 4 Felder aus deinem Frontend
        feedback_entry = {
            "timestamp": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d %H:%M:%S %z"),
            "original": data.get("1. original"),
            "correction": data.get("2. correction"),
            "confidence": data.get("3. confidence"),
            "image_id": data.get("4. image_id", None)
        }

        # Datei vorbereiten, falls sie noch nicht existiert
        if not os.path.exists(FEEDBACK_FILE):
            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

        # Vorhandenen Inhalt laden
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            feedback_data = json.load(f)

        # Neuen Eintrag anhängen
        feedback_data.append(feedback_entry)

        # Zurückschreiben
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        return {"status": "ok", "entry": feedback_entry}

    except Exception as e:
        print("⚠️ Fehler beim Einlesen des Feedback-Requests:", e)
        return {"status": "error", "message": str(e)}
