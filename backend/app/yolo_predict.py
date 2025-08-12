# app/yolo_predict.py

from ultralytics import YOLO
from PIL import Image
import io

# Vortrainiertes YOLO-Modell laden (einmalig)
MODELL = "yolov8n.pt"       # "nano"-Version: sehr schnell, Alternativen: small, medium, large, xlarge
#MODELL = "yolov8s.pt"
#MODELL = "yolov8m.pt"
#MODELL = "yolo11n.pt"
#MODELL = "yolo11s.pt"
#MODELL = "yolo11m.pt"
#MODELL = "yolo11l.pt"
#MODELL = "yolo11x.pt"
model = YOLO(MODELL)

# Funktion ist ein Platzhalter für die spätere YOLO-Erkennung
def run_inference(image_bytes: bytes) -> dict:
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