# app/yolo_predict.py

# Diese Funktion ist ein Platzhalter für die spätere YOLO-Erkennung
def run_inference(image_bytes: bytes) -> dict:
    # Beispielhafte Rückgabe mit einem "erkanntem" Apfel
    return {
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
    }
