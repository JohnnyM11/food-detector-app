from fastapi import FastAPI, UploadFile, File       # FastApi als Webframework für die API
from fastapi.middleware.cors import CORSMiddleware  # ermöglicht Cross-Origin-Zugriffe (z.B. von http://localhost:5173)
from yolo_predict import run_inference              # eigene Modell-Logik, später für YOLO-Modell-Anbindung

from fastapi import Request         # für "feedback.json" benötigt
from datetime import datetime       # für "feedback.json" benötigt
import json                         # für "feedback.json" benötigt
import os                           # für "feedback.json" benötigt

app = FastAPI()                                     # Erstellen einer FastApi-App-Instanz

# CORS aktivieren für Frontend-Zugriff (z. B. React auf localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                            # "*" = alle erlauben; später ggf. auf Frontend-URL begrenzen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict")                               # Endpunkt /predict, der ein Bild erwartet und später eine Vorhersage zurückgibt
async def predict(file: UploadFile = File(...)):
    image_bytes = await file.read()                 # Bild wird als Byte-Daten eingelesen
    result = run_inference(image_bytes)             # Übergabe ans Modell
    return { "items": result["predictions"] }       # Rückgabe als JSON

@app.get("/labels")
async def get_labels():
    # Gibt alle Labels zurück, die das Modell erkennen kann
    from yolo_predict import model
    return {"labels": list(model.names.values())}

FEEDBACK_FILE = "feedback/feedback.json"

@app.post("/feedback")
async def receive_feedback(request: Request):
    try:
        data = await request.json()
        print("DEBUG FEEDBACK:", data)

        # Zeitstempel automatisch hinzufügen
        feedback_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "original": data.get("original"),
            "correction": data.get("correction"),
            "confidence": data.get("confidence"),
            "image_id": data.get("image_id", None)
        }

        if not os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

        # Bestehende Datei laden
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            feedback_data = json.load(f)

        feedback_data.append(feedback_entry)

        # Feedbackdaten zurück in Datei speichern
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=2)

        return {"status": "ok", "entry": feedback_entry}

    except Exception as e:
            print("⚠️ Fehler beim Einlesen des Feedback-Requests:", e)
            return {"status": "error", "message": str(e)}
    