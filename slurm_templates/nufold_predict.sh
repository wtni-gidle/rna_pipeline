#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --cpus-per-task=###CPUS###
#SBATCH --mem=###MEM###
#SBATCH --gres=gpu:###GPUS###
#SBATCH --time=###TIME_LIMIT###
#SBATCH --output=###LOG_FILE###

set -e

source $(conda info --base)/etc/profile.d/conda.sh
conda activate ###CONDA_ENV###

cd ###TASK_DIR###

python ###ALGO_PATH###/predict.py \
    --fasta ###INPUT_FASTA### \
    --msa ###MSA_FILE### \
    --output ###OUTPUT_DIR###/model.pdb

echo "Prediction completed"
