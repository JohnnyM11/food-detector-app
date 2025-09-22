#!/bin/bash -l

#SBATCH --job-name=trainYoloModell
#SBATCH --partition=a100						# GPU Typ = a100
#SBATCH --gres=gpu:a100:8						# GPU Anzahl = 8
#SBATCH --cpus-per-task=16           			# Startwahl für den Dataloader
#SBATCH --time=10:00:00							# Laufzeit = hh:mm:ss
#SBATCH --output=logs/%x_%j.out					# Logeinträge output
#SBATCH --error=logs/%x_%j.err					# Logeinträge error

#SBATCH --export=NONE 							# do not export environment from submitting shell

########## User-Parameter ##########
DATA_DIR="/home/vault/b116ba/b117ba60/food"
PROJECT_DIR="/home/vault/b116ba/b117ba60/food/runs"
ENV_NAME="YoloTraining"
MODEL="/home/vault/b116ba/b117ba60/food/yolov8n.pt"
EPOCHS=200										# Trainingsdurchläufe
IMGSZ=960										# Größe, auf die Bilder skaliert werden (größer = mehr Details, besser bei kleinen Objekten)
GLOBAL_BATCH=256                           		# global, wird über alle verwendeten GPUs verteilt (Wie viele Bilder gleichzeitig pro Schritt verarbeitet werden), alt: 128, 96, 64
RUN_NAME="yolov8n_food_$(date +%Y%m%d_%H%M)"
WORKERS=$SLURM_CPUS_PER_TASK               		# Dataloader-Threads (Anzahl CPU-Threads, i.d.R. 2 pro GPU)
####################################

# 1) Diagnose-Ausgaben fürs Log
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "HOSTNAME: $(hostname)"
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"

# 2) Module & Conda-vEnv
module load python/3.9-anaconda
source $(conda info --base)/etc/profile.d/conda.sh
conda activate "$ENV_NAME"

# 3) Ordner erstellen, falls nicht vorhanden
mkdir -p "$PROJECT_DIR" logs

# 4) Training starten
# Hinweis: Ultralytics erkennt device=0,1,... und nutzt DDP (DistributedDataParallel) automatisch
# cache=ram -> Lade alle Bilder einmal in RAM (schnelleres Training möglich, aber viel RAM benötigt)
# patience=40 -> Early Stopping: Wenn Validierung 40 Epochen lang nicht besser wird, bricht Training ab
# Alternativ zu "yolo" -> python -m ultralytics
yolo detect train \
  model="$MODEL" \
  data="$DATA_DIR/data.yaml" \
  epochs="$EPOCHS" \
  imgsz="$IMGSZ" \
  batch="$GLOBAL_BATCH" \
  device=0,1,2,3,4,5,6,7 \
  workers="$WORKERS" \
  patience=60 \
  seed=0 \
  project="$PROJECT_DIR" \
  name="$RUN_NAME"

# 5) Kurze Info zum Output
echo "Fertig. Ergebnisse liegen in: ${PROJECT_DIR}/${RUN_NAME}"
