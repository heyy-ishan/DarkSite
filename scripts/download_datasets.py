# download_datasets.py
# Downloads external dark pattern datasets for training
#
# Dataset:
#   Yada et al. (IEEE BigData 2022) — balanced dark + non-dark texts (~3,600 samples)
#   Built on top of Mathur/Princeton (CSCW 2019) 1,818 dark pattern texts
#   with added clean negative samples from the same e-commerce sites.
#
# OUTPUT:
#   data/external/yada/dataset.tsv

import json
import argparse
import logging
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXTERNAL_DIR = PROJECT_ROOT / "data" / "external"


def setup_logging():
    named_logger = logging.getLogger("darksite")
    named_logger.setLevel(logging.INFO)
    if not named_logger.handlers:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        named_logger.addHandler(sh)
    return named_logger


def run_command(cmd, cwd=None):
    """Run a shell command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Command failed: {cmd}\n{result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False


def download_yada():
    """
    Download Yada et al. dark pattern dataset.
    Source: https://github.com/yamanalab/ec-darkpattern
    Contains: ~3,600 balanced dark + non-dark pattern texts (TSV)
    Built on Mathur/Princeton 1,818 dark pattern texts + clean negatives.
    """
    dest = EXTERNAL_DIR / "yada"
    dest.mkdir(parents=True, exist_ok=True)

    if (dest / "dataset.tsv").exists():
        logger.info("Yada dataset already downloaded")
        return True

    logger.info("Downloading Yada et al. dataset...")

    success = run_command(
        "git clone --depth 1 https://github.com/yamanalab/ec-darkpattern.git temp_yada",
        cwd=str(EXTERNAL_DIR),
    )

    if not success:
        logger.error("Failed to clone Yada repo. Check your internet connection.")
        return False

    temp_dir = EXTERNAL_DIR / "temp_yada"
    dataset_dir = temp_dir / "dataset"

    if dataset_dir.exists():
        for f in dataset_dir.glob("*.tsv"):
            shutil.copy2(f, dest)
            logger.info(f"  Copied: {f.name}")

    shutil.rmtree(temp_dir, ignore_errors=True)

    tsv_files = list(dest.glob("*.tsv"))
    if tsv_files:
        with open(tsv_files[0], "r", encoding="utf-8") as f:
            lines = f.readlines()
        logger.info(f"Yada dataset ready: {len(lines) - 1} samples in {dest}")  # -1 for header
        return True
    else:
        logger.error("Yada dataset: no TSV files found")
        return False


def verify():
    """Print status of external datasets."""
    logger.info("\n" + "=" * 60)
    logger.info("EXTERNAL DATASET STATUS")
    logger.info("=" * 60)

    yada_tsv = EXTERNAL_DIR / "yada" / "dataset.tsv"
    if yada_tsv.exists():
        with open(yada_tsv, "r", encoding="utf-8") as f:
            n_lines = sum(1 for _ in f) - 1
        logger.info(f"  Yada:  ✓ {n_lines} samples (balanced dark + clean)")
        logger.info(f"         Includes Mathur/Princeton dark pattern texts")
    else:
        logger.info(f"  Yada:  ✗ Not downloaded")
        logger.info(f"         Run: python download_datasets.py")

    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Download external dark pattern datasets")
    parser.add_argument("--verify", action="store_true", help="Check dataset status only")

    args = parser.parse_args()
    setup_logging()

    logger.info("External Dark Pattern Dataset Downloader")
    logger.info(f"Output directory: {EXTERNAL_DIR}")

    if args.verify:
        verify()
        return

    download_yada()
    verify()


if __name__ == "__main__":
    main()
