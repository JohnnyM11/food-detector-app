#!/bin/bash -l
#SBATCH --job-name=resumeYolo_staging
#SBATCH --partition=a100
#SBATCH --gres=gpu:a100:8
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH --export=NONE

unset SLURM_EXPORT_ENV

########## User-Parameter ##########
VAULT_DIR="/home/vault/b116ba/b117ba60/food"
PROJECT_DIR="${VAULT_DIR}/runs"
ENV_NAME="YoloTraining"

# (1) Der ursprüngliche Run-Ordnername (bitte anpassen!)
# Beispiel: "yolov8n_food_staging20250911_1530"
RESUME_RUN_NAME="yolov8n_food_staging20250911_1235"

# (2) Pfad zum Checkpoint, von dem fortgesetzt werden soll:
CKPT="${PROJECT_DIR}/${RESUME_RUN_NAME}/weights/last.pt"

# Trainings-Parameter (gleich lassen wie zuvor)
EPOCHS=1000
IMGSZ=960
BATCH=256
WORKERS=12
PATIENCE=80
AMP=True
MULTI_SCALE=True
COS_LR=True
CLOSE_MOSAIC=30
####################################

set -euo pipefail

# 0) in Vault Datenordner wechseln (Logs hier sammeln), ggf. Ordner erstellen
cd "$VAULT_DIR"
mkdir -p "$PROJECT_DIR" logs

# 1) Diagnose-Ausgaben fürs Log
echo "=== Resume-Job Start ==="
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "HOSTNAME: $(hostname)"
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "RESUME_RUN_NAME: $RESUME_RUN_NAME"
echo "CKPT: $CKPT"

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
  if try_stage_to_dir "$TMPDIR" "food"; then
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

# Optional: Auto-Requeue-Trap (nur falls --signal/--requeue oben aktiviert wurden)
trap 'echo "[INFO] Caught USR1 → scontrol requeue $SLURM_JOB_ID"; scontrol requeue $SLURM_JOB_ID; exit 0' USR1 || true

# 4) Training FORTSETZEN
# WICHTIG:
# - project/name auf den ALTEN Run setzen → gleiche Ordner/Logs
# - model="$CKPT" & resume=True
# - epochs=1000 beibehalten: Ultralytics zählt ab der im Checkpoint gespeicherten Epoche weiter
yolo detect train \
  model="$CKPT" \
  resume=True \
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
  name="$RESUME_RUN_NAME"

# 5) Kurze Info zum Output
echo "Fertig. Ergebnisse liegen in: ${PROJECT_DIR}/${RESUME_RUN_NAME}"
echo "=== Resume-Job Ende ==="
