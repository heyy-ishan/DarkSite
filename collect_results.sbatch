#!/bin/bash
#SBATCH --job-name=darksite_results
#SBATCH --account=torch_pr_932_general
#SBATCH --output=logs/results_%j.out
#SBATCH --error=logs/results_%j.err
#SBATCH --time=00:30:00
#SBATCH --mem=8GB
#SBATCH --cpus-per-task=2

# Collect and summarize results after all training is done

set -euo pipefail

mkdir -p logs

module purge
module load anaconda3/2025.06

cd /scratch/ig2671/DarkSite

# Quoted env vars for safety under set -u
export CONDA_ENVS_PATH="/scratch/ig2671/conda_envs"
export CONDA_PKGS_DIRS="/scratch/ig2671/conda_pkgs"
export PIP_CACHE_DIR="/scratch/ig2671/pip_cache"

# Initialize and activate conda environment from scratch
eval "$(conda shell.bash hook)"
conda activate /scratch/ig2671/conda_envs/darksite

echo "=================================================="
echo "Collecting DarkSite Ablation Results"
echo "=================================================="

# Collect results from all completed runs
python scripts/run_ablations.py --collect-only

# Generate summary statistics
python -c "
import json
from pathlib import Path

results_file = Path('models/ablation_results.json')
if results_file.exists():
    with open(results_file) as f:
        results = json.load(f)

    print('\nAblation Study Results Summary:')
    print('='*60)

    for variant, data in results.items():
        if 'metrics' in data and data['metrics']:
            metrics = data['metrics']
            if 'binary_f1' in metrics:
                f1 = metrics['binary_f1']
                print(f'{variant:20} Binary F1: {f1[\"mean\"]:.3f} ± {f1[\"std\"]:.3f}')
else:
    print('No results file found yet.')
"

echo "Results saved to models/ablation_results.json"