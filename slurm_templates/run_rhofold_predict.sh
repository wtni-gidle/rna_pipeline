#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
###SBATCH --account=###ACCOUNT###
#SBATCH --partition=###PARTITION###
#SBATCH --nodes=1
###SBATCH --gpus-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=###MEM###
#SBATCH --output=###OE_FILE###
#SBATCH --error=###OE_FILE###
#SBATCH --export=ALL
#SBATCH -t ###TIME_LIMIT###

# make the script stop when error (non-true exit code) occurs
set -e

############################################################
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('conda' 'shell.bash' 'hook' 2> /dev/null)"
eval "$__conda_setup"
unset __conda_setup
# <<< conda initialize <<<
############################################################

server=###SERVER###
if [[ "$server" == "delta" ]]; then
    env_path=/projects/bcnv/zshan1/miniconda3/envs/rhofold/bin/activate
    program_dir=/work/nvme/bbgs/zheng2/programs/RhoFold
elif [[ "$server" == "th-hpc6" ]]; then
    env_path=/fs6/home/casp_2026/library/bin/miniconda3/envs/rhofold/bin/activate
    program_dir=/fs6/home/casp_2026/applications/RhoFold
else
    echo "Error: Unrecognized server '$server'."
    exit 1
fi

source $env_path
cd $program_dir

input_fasta=###INPUT_FASTA###
output_dir=###OUTPUT_DIR###

SECONDS=0   # 开始计时

python inference.py \
    --input_fas $input_fasta \
    --output_dir $output_dir \
    --input_a3m $output_dir/seq.a3m \
    --relax_steps 0 \
    --device cuda:0

echo "Total runtime (seconds): $SECONDS"
echo "done"
