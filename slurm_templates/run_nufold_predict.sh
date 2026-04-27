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
#SBATCH -t ###TIME###

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
    env_path=/projects/bcnv/zshan1/miniconda3/envs/nufold_P/bin/activate
    program_dir=/work/nvme/bbgs/zheng2/programs/NuFold
elif [[ "$server" == "th-hpc6" ]]; then
    env_path=/fs6/home/casp_2026/library/bin/miniconda3/envs/nufold_P/bin/activate
    program_dir=/fs6/home/casp_2026/applications/NuFold
else
    echo "Error: Unrecognized server '$server'."
    exit 1
fi

source $env_path
cd $program_dir

input_fasta=###INPUT_FASTA###
output_dir=###OUTPUT_DIR###
num_seeds=###NUM_SEEDS###
rank=###RANK###
target_name=$(basename $input_fasta | cut -d. -f1)

SECONDS=0   # 开始计时

# secondary structure
if [ ! -f $output_dir/$target_name.ipknot.ss ]; then
    ./ipknot-1.1.0-x86_64-linux/ipknot $input_fasta > $output_dir/$target_name.ipknot.ss
fi

cmd="python3 run_nufold.py \
  --ckpt_path checkpoints/global_step145245.pt \
  --input_fasta $input_fasta \
  --input_dir $output_dir/ \
  --output_dir $output_dir \
  --config_preset initial_training \
  --num_seeds $num_seeds"

if [ "$rank" = "true" ]; then
  cmd="$cmd --rank_by_plddt"
fi

eval $cmd

echo "Total runtime (seconds): $SECONDS"
echo "done"
