# app/yolo_predict.py

import io
import os
from PIL import Image
from ultralytics import YOLO

# Modell-Auswahl
# Standardmodelle von YOLO-Hub:
#MODELL = "yolov8n.pt"       # "nano"-Version: sehr schnell, Alternativen: small, medium, large, xlarge
#MODELL = "yolov8s.pt"
#MODELL = "yolov8m.pt"
#MODELL = "yolo11n.pt"
#MODELL = "yolo11s.pt"
#MODELL = "yolo11m.pt"
#MODELL = "yolo11l.pt"
#MODELL = "yolo11x.pt"

# Eigenes trainiertes Modell im backend/models/ Ordner:
MODELL = "models/yolov8n_best.pt"

if not os.path.isabs(MODELL) and os.path.exists(os.path.join(os.path.dirname(__file__), MODELL)):
    model_path = os.path.join(os.path.dirname(__file__), MODELL)
else:
    model_path = MODELL

model = YOLO(model_path)

def run_inference(image_bytes: bytes) -> dict:
    """Führt Inferenz auf einem Bild aus und gibt Vorhersagen zurück."""
    # Bilddaten aus Bytes lesen
    image = Image.open(io.BytesIO(image_bytes))
    # Inference mit YOLO
    results = model(image)
    
    # Vorhersagen extrahieren
    predictions = []
    for r in results:
        for box in r.boxes:
            class_id = int(box.cls)
            confidence = float(box.conf)
            label = model.names[class_id]
            predictions.append({
                "class_id": class_id,
                "label": label,
                "confidence": round(confidence, 3)
            })

    return {"predictions": predictions}


    # Beispielhafte Rückgabe mit einem "erkanntem" Apfel
    """ return {
        "items": [
            {
                "label": "Apfel", 
                "confidence": 0.95, 
                "nutrition": {
                    "kcal": 52, 
                    "protein": 0.3, 
                    "fat": 0.2, 
                    "carbs": 14
                }
            }
        ]
    } """

def get_model_name():
    return MODELL