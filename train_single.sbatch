#!/bin/bash
#SBATCH --job-name=darksite_test
#SBATCH --account=torch_pr_932_general
#SBATCH --partition=l40s_public
#SBATCH --output=logs/darksite_test_%j.out
#SBATCH --error=logs/darksite_test_%j.err
#SBATCH --time=01:50:00
#SBATCH --gres=gpu:l40s:1
#SBATCH --mem=46GB
#SBATCH --cpus-per-task=8

# Quick single training run for testing
# Use this first to verify everything works before running full ablation

set -euo pipefail

# ==================== SETUP ====================
module purge
module load anaconda3/2025.06

mkdir -p logs
cd /scratch/ig2671/DarkSite

# Point caches to scratch (home quota too small for conda/pip)
export CONDA_ENVS_PATH="/scratch/ig2671/conda_envs"
export CONDA_PKGS_DIRS="/scratch/ig2671/conda_pkgs"
export PIP_CACHE_DIR="/scratch/ig2671/pip_cache"
export XDG_CACHE_HOME="/scratch/ig2671/.cache"
export TMPDIR="/scratch/ig2671/tmp"
mkdir -p "${TMPDIR}" "${XDG_CACHE_HOME}"

# Reduce CUDA fragmentation on long runs
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# ==================== ENV ACTIVATION ====================
# Anaconda 2025.06 activate.d/qt-main_activate.sh references unbound QT_XCB_GL_INTEGRATION,
# which trips `set -u`. Disable nounset for conda activation only, re-enable after.
set +u
eval "$(conda shell.bash hook)"
conda activate /scratch/ig2671/conda_envs/darksite
[ -f /scratch/ig2671/.wandb_env ] && source /scratch/ig2671/.wandb_env
set -u

echo "=================================================="
echo "Job: ${SLURM_JOB_ID} on $(hostname)"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Time: $(date)"
echo "=================================================="

# Fail fast if torch is missing (no in-job pip install — avoids env corruption)
python -c "import torch; print('PyTorch', torch.__version__, 'CUDA:', torch.cuda.is_available())"

# ==================== GPU UTIL WATCHDOG ====================
UTIL_LOG="logs/util_${SLURM_JOB_ID}.log"
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

# ==================== TRAIN ====================
OUTPUT_DIR="models/test_run"
RESUME_ARG=""
LATEST_CKPT=""
if [ -d "${OUTPUT_DIR}" ]; then
    LATEST_CKPT="$(ls -t "${OUTPUT_DIR}"/checkpoint_epoch*.pt 2>/dev/null | head -n1 || true)"
fi
if [ -n "${LATEST_CKPT}" ] && [ -f "${LATEST_CKPT}" ]; then
    RESUME_ARG="--resume ${LATEST_CKPT}"
    echo "Resuming from ${LATEST_CKPT}"
fi

python scripts/train.py \
    --seed 42 \
    --epochs 3 \
    --batch-size 16 \
    --amp \
    --num-workers 4 \
    --output-dir "${OUTPUT_DIR}" \
    --save-every 1 \
    ${RESUME_ARG}

echo "Test completed at $(date). Check ${OUTPUT_DIR}/ and ${UTIL_LOG}"
