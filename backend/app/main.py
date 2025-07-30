from fastapi import FastAPI, UploadFile, File       # FastApi als Webframework für die API
from fastapi.middleware.cors import CORSMiddleware  # ermöglicht Cross-Origin-Zugriffe (z.B. von http://localhost:5173)
from yolo_predict import run_inference          # eigene Modell-Logik, später für YOLO-Modell-Anbindung

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
