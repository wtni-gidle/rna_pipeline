#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
###SBATCH --account=###ACCOUNT###
#SBATCH --partition=###PARTITION###
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=###NCPU###
#SBATCH --cpus-per-task=1
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
# 根据server来设置program_dir
if [[ "$server" == "delta" ]]; then
    program_dir=/work/nvme/bbgs/zheng2/programs/NuFold/rMSA
elif [[ "$server" == "hpc6" ]]; then
    program_dir=/fs6/home/casp_2026/applications/NuFold/rMSA
else
    echo "Error: Unrecognized server '$server'."
    exit 1
fi

cd $program_dir

input_fasta=###INPUT_FASTA###
output_dir=###OUTPUT_DIR###
ncpu=###NCPU###

SECONDS=0   # 开始计时

# Run rMSA
./rMSA.pl $input_fasta -cpu=$ncpu -outdir=$output_dir

echo "Total runtime (seconds): $SECONDS"
echo "done"
