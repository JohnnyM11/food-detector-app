#!/bin/bash -l

#SBATCH --job-name=trainYoloModell_staging09
#SBATCH --partition=a100						# GPU Typ = a100
#SBATCH --gres=gpu:a100:8						# GPU Anzahl = 8
#SBATCH --cpus-per-task=16           			# Startwahl für den Dataloader
#SBATCH --time=24:00:00							# Laufzeit = hh:mm:ss
#SBATCH --output=logs/%x_%j.out					# Logeinträge output
#SBATCH --error=logs/%x_%j.err					# Logeinträge error

#SBATCH --export=NONE 							# do not export environment from submitting shell

unset SLURM_EXPORT_ENV							# gemäß Doku: https://doc.nhr.fau.de/data/staging/

########## User-Parameter ##########
VAULT_DIR="/home/vault/b116ba/b117ba60/food09"
PROJECT_DIR="${VAULT_DIR}/runs"
ENV_NAME="YoloTraining"
MODEL="/home/vault/b116ba/b117ba60/food/yolov8n.pt"
EPOCHS=1000										# Trainingsdurchläufe
IMGSZ=640										# Größe, auf die Bilder skaliert werden (größer = mehr Details, besser bei kleinen Objekten)
BATCH=512                           		# GLOBAL_BATCH=256 -> global, wird über alle verwendeten GPUs verteilt (Wie viele Bilder gleichzeitig pro Schritt verarbeitet werden), alt: 128, 96, 64
RUN_NAME="yolov8n_food09_staging$(date +%Y%m%d_%H%M)"
WORKERS=12										# $SLURM_CPUS_PER_TASK (=16)	# Dataloader-Threads (Anzahl CPU-Threads, i.d.R. 2 pro GPU)
PATIENCE=80
AMP=True
MULTI_SCALE=True
COS_LR=True
CLOSE_MOSAIC=30
####################################

set -euo pipefail

# 0) in Vault Datenordner wechseln (Logs hier sammeln), ggf. Ordner erstellen, falls nicht vorhanden
cd "$VAULT_DIR"
mkdir -p "$PROJECT_DIR" logs

# 1) Diagnose-Ausgaben fürs Log
echo "=== Job Start ==="
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "HOSTNAME: $(hostname)"
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"

# 2) Module & Conda-vEnv
module load python/3.9-anaconda
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

# 3) Daten staging (in/out) - bevorzugt $TMPDIR, sonst Vault
DATA_DIR="$VAULT_DIR"   # Default: direkt aus Vault trainieren
STAGED=0                # 1 falls wir auf $TMPDIR kopiert haben

# 3a) Datensatzgröße in KB (für Platzcheck) ermitteln
DS_KB=$(du -sk "$VAULT_DIR" | awk '{print $1}')
NEED_KB=$(( DS_KB + DS_KB / 5 ))  # +20% Puffer

try_stage_to_dir () {
  local TARGET="$1"
  local SUBDIR="$2"   # z.B. food
  local DEST="${TARGET%/}/${SUBDIR}"

  # Freien Platz in KB ermitteln (POSIX-kompatibel)
  local FREE_KB
  FREE_KB=$(df -Pk "$TARGET" 2>/dev/null | awk 'NR==2 {print $4}')
  if [ -z "${FREE_KB:-}" ]; then
    echo "[WARN] Konnte freien Platz auf $TARGET nicht ermitteln."
    return 1
  fi

  echo "[INFO] Freier Platz auf $TARGET: ~$((FREE_KB/1024/1024)) GB | benötigt: ~$((NEED_KB/1024/1024)) GB"

  if [ "$FREE_KB" -lt "$NEED_KB" ]; then
    echo "[WARN] Zu wenig Platz auf $TARGET."
    return 1
  fi

  echo "[INFO] Stage Daten → $DEST (rsync, read-only Quelle bleibt im Vault erhalten)"
  mkdir -p "$DEST"
  # rsync: -a (Archiv), -h (human), --delete (Ziel spiegeln), --info=progress2 (Fortschritt)
  rsync -ah --delete --info=progress2 "$VAULT_DIR"/ "$DEST"/
  DATA_DIR="$DEST"
  STAGED=1
  return 0
}

# 3b) bevorzugt $TMPDIR
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
  echo "[INFO] $TMPDIR erkannt → versuche Staging dorthin…"
  if try_stage_to_dir "$TMPDIR" "food09"; then
    echo "[INFO] Daten aus $DATA_DIR werden für das Training verwendet."
  else
    echo "[WARN] Staging nach \$TMPDIR fehlgeschlagen oder zu wenig Platz."
  fi
fi

# 3c) ansonsten Training direkt aus Vault
if [ "$STAGED" -eq 0 ]; then
  echo "[INFO] Training läuft direkt von VAULT: $DATA_DIR"
fi

echo "[INFO] FINAL DATA_DIR = $DATA_DIR"
echo "[INFO] PROJECT_DIR    = $PROJECT_DIR"
echo "[INFO] MODEL       = $MODEL"


# 4) Training starten
# Hinweis: Ultralytics erkennt device=0,1,... und nutzt DDP (DistributedDataParallel) automatisch
# cache=ram -> Lade alle Bilder einmal in RAM (schnelleres Training möglich, aber viel RAM benötigt)
# amp=True -> „Automatic Mixed Precision“: nutzt halbgenaue Berechnungen (FP16), wo es sicher ist -> schnelleres Training und weniger Speicherverbrauch auf GPUs
# patience=40 -> Early Stopping: Wenn Validierung 40 Epochen lang nicht besser wird, bricht Training ab
# Alternativ zu "yolo" -> python -m ultralytics (benötigt ultralytics-version >8.x)
yolo detect train \
  model="$MODEL" \
  data="$DATA_DIR/data.yaml" \
  epochs="$EPOCHS" \
  imgsz="$IMGSZ" \
  batch="$BATCH" \
  device=0,1,2,3,4,5,6,7 \
  workers="$WORKERS" \
  amp="$AMP" \
  patience="$PATIENCE" \
  multi_scale="$MULTI_SCALE" \
  cos_lr="$COS_LR" \
  close_mosaic="$CLOSE_MOSAIC" \
  seed=0 \
  project="$PROJECT_DIR" \
  name="$RUN_NAME"

# 5) Kurze Info zum Output
echo "Fertig. Ergebnisse liegen in: ${PROJECT_DIR}/${RUN_NAME}"
echo "=== Job Ende ==="
