#!/bin/bash
#SBATCH --job-name=darksite_ablation
#SBATCH --account=torch_pr_932_general
#SBATCH --partition=l40s_public
#SBATCH --output=logs/darksite_ablation_%A_%a.out
#SBATCH --error=logs/darksite_ablation_%A_%a.err
#SBATCH --time=47:00:00
#SBATCH --gres=gpu:l40s:1
#SBATCH --mem=46GB
#SBATCH --cpus-per-task=8
#SBATCH --array=0-20%3  # 21 jobs total (7 variants x 3 seeds), max 3 concurrent

# DarkSite: Multi-Modal Dark Pattern Detection
# Ablation study training on NYU Torch HPC

set -euo pipefail

# ==================== SETUP ====================
module purge
module load anaconda3/2025.06

mkdir -p logs
cd /scratch/ig2671/DarkSite

# Point caches to scratch
export CONDA_ENVS_PATH="/scratch/ig2671/conda_envs"
export CONDA_PKGS_DIRS="/scratch/ig2671/conda_pkgs"
export PIP_CACHE_DIR="/scratch/ig2671/pip_cache"
export XDG_CACHE_HOME="/scratch/ig2671/.cache"
export TMPDIR="/scratch/ig2671/tmp"
mkdir -p "${TMPDIR}" "${XDG_CACHE_HOME}"

# Reduce CUDA fragmentation on long runs
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# ==================== ENV ACTIVATION ====================
# Anaconda activate scripts reference unbound vars → trip `set -u`. Toggle off/on.
set +u
eval "$(conda shell.bash hook)"
conda activate /scratch/ig2671/conda_envs/darksite
[ -f /scratch/ig2671/.wandb_env ] && source /scratch/ig2671/.wandb_env
set -u

# Fail fast if torch missing — no in-job pip install (race corruption risk in arrays)
python -c "import torch; print('PyTorch', torch.__version__, 'CUDA:', torch.cuda.is_available())"

# ==================== VARIANT DISPATCH ====================
VARIANTS=("full" "text-only" "visual-only" "structural-only" "visual-text" "text-structural" "visual-structural")
SEEDS=(42 123 456)

VARIANT_IDX=$((SLURM_ARRAY_TASK_ID / 3))
SEED_IDX=$((SLURM_ARRAY_TASK_ID % 3))
VARIANT="${VARIANTS[${VARIANT_IDX}]}"
SEED="${SEEDS[${SEED_IDX}]}"

echo "=================================================="
echo "Job ID: ${SLURM_JOB_ID} / Array Task: ${SLURM_ARRAY_TASK_ID}"
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Variant: ${VARIANT}  Seed: ${SEED}"
echo "Time: $(date)"
echo "=================================================="

case "${VARIANT}" in
    "full")              DISABLE_ARG="" ;;
    "text-only")         DISABLE_ARG="--disable-branches visual,structural" ;;
    "visual-only")       DISABLE_ARG="--disable-branches text,structural" ;;
    "structural-only")   DISABLE_ARG="--disable-branches visual,text" ;;
    "visual-text")       DISABLE_ARG="--disable-branches structural" ;;
    "text-structural")   DISABLE_ARG="--disable-branches visual" ;;
    "visual-structural") DISABLE_ARG="--disable-branches text" ;;
    *) echo "Unknown variant: ${VARIANT}" >&2; exit 1 ;;
esac

# ==================== GPU UTIL WATCHDOG ====================
UTIL_LOG="logs/util_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log"
echo "timestamp,gpu_util_pct,mem_used_mib,mem_total_mib" > "${UTIL_LOG}"
(
    while true; do
        STATS=$(nvidia-smi \
            --query-gpu=utilization.gpu,memory.used,memory.total \
            --format=csv,noheader,nounits 2>/dev/null \
            | head -1 | tr -d ' ')
        [ -n "${STATS}" ] && echo "$(date +%s),${STATS}" >> "${UTIL_LOG}"
        sleep 30
    done
) &
WATCHDOG_PID=$!
trap "kill ${WATCHDOG_PID} 2>/dev/null || true" EXIT

# ==================== RESUME DETECTION ====================
OUTPUT_DIR="models/${VARIANT}/seed_${SEED}"
RESUME_ARG=""
LATEST_CKPT=""
if [ -d "${OUTPUT_DIR}" ]; then
    LATEST_CKPT="$(ls -t "${OUTPUT_DIR}"/checkpoint_epoch*.pt 2>/dev/null | head -n1 || true)"
fi
if [ -n "${LATEST_CKPT}" ] && [ -f "${LATEST_CKPT}" ]; then
    RESUME_ARG="--resume ${LATEST_CKPT}"
    echo "Resuming from ${LATEST_CKPT}"
else
    echo "Starting fresh training (no checkpoints found)"
fi

# ==================== TRAIN ====================
python scripts/train.py \
    --seed "${SEED}" \
    --epochs 30 \
    --batch-size 16 \
    --lr-backbone 1e-5 \
    --lr-new 1e-4 \
    --weight-decay 0.01 \
    --patience 7 \
    --amp \
    --num-workers 8 \
    --output-dir "${OUTPUT_DIR}" \
    --save-every 5 \
    ${RESUME_ARG} \
    ${DISABLE_ARG}

echo "Training completed: ${VARIANT} (seed=${SEED}) at $(date)"
