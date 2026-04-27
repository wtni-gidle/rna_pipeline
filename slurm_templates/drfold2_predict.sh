#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --cpus-per-task=###CPUS###
#SBATCH --mem=###MEM###
#SBATCH --gres=gpu:###GPUS###
#SBATCH --time=###TIME_LIMIT###
#SBATCH --output=###LOG_FILE###

set -e

# Activate conda environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate ###CONDA_ENV###

# Change to task directory
cd ###TASK_DIR###

# Run DRfold2 prediction
python ###ALGO_PATH###/predict.py \
    --input ###INPUT_FASTA### \
    --output ###OUTPUT_DIR###/predicted_structure.pdb

echo "DRfold2 prediction completed successfully"
