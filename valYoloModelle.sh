#!/bin/bash -l
#SBATCH --job-name=valCompare
#SBATCH --partition=a100
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=4
#SBATCH --time=10:00:00
#SBATCH --output=valComp/logs/%x_%A_%a.out
#SBATCH --error=valComp/logs/%x_%A_%a.err
#SBATCH --export=NONE
#SBATCH --array=0-5%2      # 2 Modelle x 3 imgsz = 6 Tasks, max. 2 parallel

# ------------------------- User-Parameter -------------------------
DATA_DIR="/home/vault/b116ba/b117ba60/food09"                 # nur Check/Info
PROJECT_DIR="/home/vault/b116ba/b117ba60/valComp/runs"
LOG_ROOT="/home/vault/b116ba/b117ba60/valComp/logs"
ENV_NAME="YoloTraining"
WORKERS=4
AMP=True
SPLIT="test"

# YAMLs
DATA_YML64="/home/vault/b116ba/b117ba60/food/data.yaml"       # 64er names (Quelle für Remap)
KEEP_YML57="/home/vault/b116ba/b117ba60/food09/data.yaml"     # 57er names (direkte Val)

# Modelle (GENAU 2!)
MODELS=(
"/home/vault/b116ba/b117ba60/food09/runs/yolo11s_food09_staging20250915_1625/weights/best.pt"
"/home/vault/b116ba/b117ba60/food09/runs/yolo11m_food09_staging20250915_2007/weights/best.pt"
)
SIZES=(512 640 768)
# ------------------------------------------------------------------

set -euo pipefail
mkdir -p "$PROJECT_DIR" "$LOG_ROOT"

# Helpers für Run-Tag/-ID
get_run_tag() { basename "$(dirname "$(dirname "$1")")"; }
get_run_id()  { get_run_tag "$1" | sed -n 's/.*_\([0-9][0-9]*\)$/\1/p'; }

# Paarlabel (aufsteigend)
ID1="$(get_run_id "${MODELS[0]}")"; ID2="$(get_run_id "${MODELS[1]}")"
if [[ -z "$ID1" || -z "$ID2" ]]; then echo "❌ Konnte Run-IDs nicht aus Pfaden lesen."; exit 2; fi
if (( ID1 <= ID2 )); then PAIR_LABEL="${ID1}-${ID2}"; else PAIR_LABEL="${ID2}-${ID1}"; fi
PAIR_DIR="${PROJECT_DIR}/${PAIR_LABEL}"
mkdir -p "$PAIR_DIR"

RUN_TAG1="$(get_run_tag "${MODELS[0]}")"
RUN_TAG2="$(get_run_tag "${MODELS[1]}")"

EXPECTED=$(( ${#MODELS[@]} * ${#SIZES[@]} ))

# Array-Index -> Modell/Größe
MID=$(( SLURM_ARRAY_TASK_ID / 3 ))
SID=$(( SLURM_ARRAY_TASK_ID % 3 ))
MODEL="${MODELS[$MID]}"
IMGSZ="${SIZES[$SID]}"

# Checks
[[ -f "$MODEL"      ]] || { echo "❌ MODEL nicht gefunden: $MODEL"; exit 2; }
[[ -f "$DATA_YML64" ]] || { echo "❌ DATA_YML64 nicht gefunden: $DATA_YML64"; exit 2; }
[[ -f "$KEEP_YML57" ]] || { echo "❌ KEEP_YML57 nicht gefunden: $KEEP_YML57"; exit 2; }
[[ -f "${DATA_DIR}/data.yaml" ]] || true

# Batch
if   [[ "$IMGSZ" -eq 512 ]]; then BATCH=128
elif [[ "$IMGSZ" -eq 640 ]]; then BATCH=64
else                               BATCH=32
fi

RUN_TAG_CUR="$(get_run_tag "$MODEL")"
RUN_ID_CUR="$(get_run_id "$MODEL")"
JOBID="${SLURM_JOB_ID:-manual}"
TASKID="${SLURM_ARRAY_TASK_ID:-0}"

module load python/3.9-anaconda
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

# -------------------- VAL (Auto 64→Remap | 57→Direct) --------------------
MODEL="$MODEL" DATA_YML64="$DATA_YML64" KEEP_YML57="$KEEP_YML57" \
PAIR_DIR="$PAIR_DIR" RUN_ID_CUR="$RUN_ID_CUR" IMGSZ="$IMGSZ" \
BATCH="$BATCH" WORKERS="$WORKERS" AMP="$AMP" SPLIT="$SPLIT" \
JOBID="$JOBID" TASKID="$TASKID" \
python - <<'PY'
import os, json, time, yaml, shutil
from pathlib import Path
from tempfile import gettempdir
from ultralytics import YOLO

def as_bool(x): return str(x).lower() in {"1","true","yes","y","t"}

MODEL      = os.environ["MODEL"]
DATA_YML64 = os.environ["DATA_YML64"]
KEEP_YML57 = os.environ["KEEP_YML57"]
PAIR_DIR   = Path(os.environ["PAIR_DIR"])
RUN_ID     = os.environ["RUN_ID_CUR"]
IMGSZ      = int(os.environ["IMGSZ"])
BATCH      = int(os.environ["BATCH"])
WORKERS    = int(os.environ.get("WORKERS","4"))
AMP        = as_bool(os.environ.get("AMP","True"))
SPLIT      = os.environ.get("SPLIT","val")
JOBID      = os.environ.get("JOBID","manual")
TASKID     = os.environ.get("TASKID","0")

with open(DATA_YML64, "r") as f: ds64 = yaml.safe_load(f)
with open(KEEP_YML57, "r") as f: ds57 = yaml.safe_load(f)
names64 = [str(n).strip() for n in ds64["names"]]
names57 = [str(n).strip() for n in ds57["names"]]

m = YOLO(MODEL)
nc_model = len(m.names)

NAME = f"valcmp-{RUN_ID}-{IMGSZ}"       # exakt die gewünschte Ordnerbenennung
PROJECT = PAIR_DIR                       # direkt in den Paarordner schreiben

def run_val(data_path: str):
    t0 = time.time()
    res = m.val(
        data=data_path, split=SPLIT,
        imgsz=IMGSZ, batch=BATCH, workers=WORKERS, amp=AMP,
        project=str(PROJECT), name=NAME, save=True, plots=True
    )
    elapsed = time.time() - t0
    out = Path(getattr(res, "save_dir", PROJECT/NAME))
    summary = getattr(res, "results_dict", {}) or {}
    summary.update({"elapsed_sec_host": round(elapsed,3),
                    "imgsz": IMGSZ, "model": MODEL, "split": SPLIT})
    (out/"results_summary.json").write_text(json.dumps(summary, indent=2))
    # optional CSV
    try:
        df = res.to_df()
        out_csv = out/"results.csv"
        try:
            import polars as pl; df.write_csv(out_csv)
        except Exception:
            import pandas as pd; df.to_pandas().to_csv(out_csv, index=False)
    except Exception:
        pass
    return out

# 64-Klassen-Modell → 57->64 Remap in TMP, aber Ausgabe direkt im Paarordner
if nc_model == len(names64) and len(names57) < len(names64):
    lookup64 = {n.lower(): i for i, n in enumerate(names64)}
    id_map = {i57: lookup64[n.lower()] for i57, n in enumerate(names57) if n.lower() in lookup64}

    root57 = Path(ds57.get("path",".")).resolve()
    src_imgs = root57/"images"/SPLIT
    src_lbls = root57/"labels"/SPLIT

    tmp_root = Path(os.environ.get("TMPDIR") or os.environ.get("SLURM_TMPDIR") or gettempdir()) / f"mapped_k57_{JOBID}_{TASKID}"
    imgs_dst = tmp_root/"images"/SPLIT
    lbls_dst = tmp_root/"labels"/SPLIT
    imgs_dst.parent.mkdir(parents=True, exist_ok=True); lbls_dst.mkdir(parents=True, exist_ok=True)
    try:
        if not imgs_dst.exists(): os.symlink(src_imgs, imgs_dst, target_is_directory=True)
    except Exception: pass

    for txt in src_lbls.rglob("*.txt"):
        rel = txt.relative_to(src_lbls)
        out = lbls_dst/rel; out.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for ln in open(txt, "r", encoding="utf-8", errors="ignore"):
            ln = ln.strip()
            if not ln: continue
            p = ln.split()
            try: cid = int(p[0])
            except: continue
            if cid not in id_map: continue
            p[0] = str(id_map[cid])
            lines.append(" ".join(p))
        out.write_text(("\n".join(lines)+"\n") if lines else "", encoding="utf-8")

    data_map = tmp_root/"data_mapped.yaml"
    data_map.write_text(yaml.safe_dump({
        "path":  str(tmp_root),
        "train": f"images/{SPLIT}",
        "val":   f"images/{SPLIT}",
        "test":  f"images/{SPLIT}",
        "names": names64
    }, sort_keys=False), encoding="utf-8")

    outdir = run_val(str(data_map))
    try: shutil.rmtree(tmp_root, ignore_errors=True)
    except Exception: pass

# 57-Klassen-Modell → direkte Val
elif nc_model == len(names57):
    outdir = run_val(KEEP_YML57)

else:
    raise RuntimeError(f"Modell hat {nc_model} Klassen – passt nicht zu 64/57.")

print(str(outdir))
PY

# ------------------------ CSV-Bau + Logs umkopieren -----------------------
PAIR_LABEL="$PAIR_LABEL" PAIR_DIR="$PAIR_DIR" PROJECT_DIR="$PROJECT_DIR" \
RUN_TAG1="$RUN_TAG1" RUN_TAG2="$RUN_TAG2" LOG_ROOT="$LOG_ROOT" \
JOBID="${SLURM_JOB_ID:-manual}" SPLIT="$SPLIT" \
python - <<'PY'
import os, csv, json, re, shutil
from pathlib import Path

PAIR_LABEL = os.environ["PAIR_LABEL"]
PAIR_DIR   = Path(os.environ["PAIR_DIR"])
PROJECT_DIR= Path(os.environ["PROJECT_DIR"])
RUN_TAG1   = os.environ["RUN_TAG1"]
RUN_TAG2   = os.environ["RUN_TAG2"]
LOG_ROOT   = Path(os.environ["LOG_ROOT"])
JOBID      = os.environ.get("JOBID","manual")
SPLIT      = os.environ.get("SPLIT","test")

# IDs ableiten
def run_id_from_tag(tag: str):
    m = re.search(r"_([0-9]+)$", tag)
    return m.group(1) if m else tag

id1 = run_id_from_tag(RUN_TAG1)
id2 = run_id_from_tag(RUN_TAG2)
if id2 < id1: id1, id2 = id2, id1

# Warten bis 6 Run-Ordner existieren (valcmp-<id>-<imgsz>)
need = {f"valcmp-{id1}-512", f"valcmp-{id1}-640", f"valcmp-{id1}-768",
        f"valcmp-{id2}-512", f"valcmp-{id2}-640", f"valcmp-{id2}-768"}
have = {p.name for p in PAIR_DIR.iterdir() if p.is_dir() and p.name.startswith("valcmp-")}
if not need.issubset(have):
    raise SystemExit(0)

# Metriken extrahieren
def metrics_from_summary(s: dict):
    def pick(key_part):
        for k,v in s.items():
            lk = k.lower()
            if lk.startswith("metrics/") and key_part in lk:
                try: return float(v)
                except: return None
        return None
    return {
        "metrics/mAP50-95": pick("map50-95"),
        "metrics/mAP50":    pick("map50"),
        "metrics/precision":pick("precision"),
        "metrics/recall":   pick("recall"),
    }

def extract_row(run_dir: Path, pair_label: str):
    sfile = run_dir/"results_summary.json"
    s = {}
    try: s = json.load(open(sfile,"r",encoding="utf-8"))
    except Exception: pass
    mets = metrics_from_summary(s)
    return {
        "pair": pair_label,
        "run_dir": run_dir.name,
        "model": s.get("model",""),
        "imgsz": s.get("imgsz",""),
        "split": s.get("split",""),
        "metrics/mAP50-95": mets.get("metrics/mAP50-95"),
        "metrics/mAP50":    mets.get("metrics/mAP50"),
        "metrics/precision":mets.get("metrics/precision"),
        "metrics/recall":   mets.get("metrics/recall"),
    }

rows = [extract_row(PAIR_DIR/f"valcmp-{id1}-{sz}", f"{id1}-{id2}") for sz in (512,640,768)]
rows += [extract_row(PAIR_DIR/f"valcmp-{id2}-{sz}", f"{id1}-{id2}") for sz in (512,640,768)]

# Paar-CSV
pair_csv = PAIR_DIR / f"compare-{id1}-{id2}.csv"
hdr = ["pair","run_dir","model","imgsz","split","metrics/mAP50-95","metrics/mAP50","metrics/precision","metrics/recall"]
with open(pair_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=hdr, delimiter=';')
    w.writeheader(); w.writerows(rows)

# compare_all.csv (append-only, oben unter runs/)
all_csv = PROJECT_DIR / "compare_all.csv"
write_header = not all_csv.exists()
with open(all_csv, "a", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=hdr, delimiter=';')
    if write_header: w.writeheader()
    w.writerows(rows)

# Logs in LOG_ROOT/<PAIR_LABEL> kopieren (nicht in den Paar-Ordner)
log_dest = LOG_ROOT / PAIR_LABEL
log_dest.mkdir(parents=True, exist_ok=True)
for lf in Path(LOG_ROOT).glob(f"valCompare_{JOBID}_*.out"):
    dst = log_dest/lf.name
    if not dst.exists(): shutil.copy2(lf, dst)
for lf in Path(LOG_ROOT).glob(f"valCompare_{JOBID}_*.err"):
    dst = log_dest/lf.name
    if not dst.exists(): shutil.copy2(lf, dst)

print(f"[PAIR READY] {PAIR_DIR}")
print(f"[PAIR CSV]  {pair_csv}")
print(f"[ALL CSV]   {all_csv}")
print(f"[LOGS]      {log_dest}")
PY

echo "✅ Job ${SLURM_ARRAY_TASK_ID} abgeschlossen."
