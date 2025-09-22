# yolo_predict.py
# ------------------------------------------------------------
# Lädt ein YOLO-Modell und führt Inferenz auf Bildbytes aus.
# Gibt ein einheitliches JSON-ähnliches Dict zurück:
# {
#   "predictions": [
#      {
#         "class_id": int,
#         "label": str,           # Klassenname aus model.names (englisch)
#         "confidence": float,    # 0..1
#         "bbox": [x1, y1, x2, y2]# optional fürs Frontend (Pixelkoordinaten)
#      }, ...
#   ]
# }
# Dazu: get_model_name() für das Frontend (Anzeige im Header).
# ------------------------------------------------------------

from ultralytics import YOLO          # Ultralytics YOLO Inferenz
from PIL import Image                 # Bildöffnung aus Bytes
import io                             # Bytes-Buffer für PIL
from pathlib import Path

# ---- Modell laden (einmalig beim Import) -------------------
# Standardmodelle von YOLO-Hub:
#MODELL = "yolov8n.pt"       # "nano"-Version: sehr schnell, Alternativen: small, medium, large, xlarge
#MODELL = "yolov8s.pt"
#MODELL = "yolov8m.pt"
#MODELL = "yolo11n.pt"
#MODELL = "yolo11s.pt"
MODELL = "yolo11m.pt"
#MODELL = "yolo11l.pt"
#MODELL = "yolo11x.pt"

# Eigenes trainiertes Modell im Ordner backend/models/:
#MODELL = "models/yolo11m-best-2007.pt"
#MODELL = "models/yolo11n-best-1257.pt"
#MODELL = "models/yolo11s-best-1625.pt"

BACKEND_DIR = Path(__file__).resolve().parents[1]
def resolve_weights(spec: str) -> str:
    looks_like_path = any(s in spec for s in ("/", "\\")) or spec.startswith((".", "..", "models"))
    return str((BACKEND_DIR / spec).resolve()) if looks_like_path else spec

model = YOLO(resolve_weights(MODELL))       # lädt Gewichte und bereitet Inferenz vor

def run_inference(image_bytes: bytes) -> dict:
    """
    Führt YOLO-Inferenz auf einem Bild (als Bytes) aus und
    liefert ein Dict mit 'predictions' (Liste von Erkennungen).
    """
    # Bytes -> PIL Image (PIL erwartet einen Datei-ähnlichen Stream)
    image = Image.open(io.BytesIO(image_bytes))

    # Inferenz: Ultralytics-API akzeptiert direkt PIL-Images
    results = model(image)

    # Vorhersagen extrahieren (pro Result-Frame die Boxes)
    predictions = []
    for r in results:
        # r.boxes enthält alle Detektionen; jede Box hat Koordinaten & Meta
        for box in r.boxes:
            class_id = int(box.cls)                 # Klassenindex (z. B. 0..N)
            confidence = float(box.conf)            # Konfidenz 0..1
            label = model.names[class_id]           # Klassenname (englisch)

            # Bounding Box als Liste [x1, y1, x2, y2] (Float -> round für saubere Ausgabe)
            # .xyxy gibt Tensor mit [x1, y1, x2, y2]; wir holen das erste Element (.tolist()[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            bbox = [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]

            predictions.append({
                "class_id": class_id,
                "label": label,
                "confidence": round(confidence, 3),
                "bbox": bbox
            })

    # Einheitliches Rückgabeformat, das das Backend / Frontend leicht weiterverarbeiten kann
    return {"predictions": predictions}


def get_model_name() -> str:
    """
    Liefert den aktuell verwendeten Modellnamen (für /model-info im Backend). 
    """
    return MODELL
