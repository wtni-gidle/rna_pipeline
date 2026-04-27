# Slurm Script Templates

这个目录存放所有算法的Slurm脚本模板。

## 模板变量系统

使用 `###KEYWORD###` 作为占位符，框架会自动替换为实际值。

### 默认可用变量

这些变量由框架自动提供，无需在 `get_template_variables()` 中定义：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `###JOB_NAME###` | 任务名称 | `predict` |
| `###PARTITION###` | Slurm分区 | `gpu` |
| `###CPUS###` | CPU核心数 | `8` |
| `###MEM###` | 内存 | `32G` |
| `###GPUS###` | GPU数量 | `1` |
| `###TIME_LIMIT###` | 时间限制 | `24:00:00` |
| `###LOG_FILE###` | 日志文件路径 | `/path/to/output/H1214/DRfold2/predict/predict.log` |
| `###INPUT_FASTA###` | 输入FASTA文件 | `/path/to/input.fasta` |
| `###OUTPUT_DIR###` | 输出目录 | `/path/to/output/H1214/DRfold2/predict` |
| `###TASK_DIR###` | 任务目录（同OUTPUT_DIR） | `/path/to/output/H1214/DRfold2/predict` |

### 自定义变量

在Task类的 `get_template_variables()` 方法中返回字典：

```python
def get_template_variables(self) -> dict[str, str]:
    return {
        "CONDA_ENV": "drfold2",
        "ALGO_PATH": "/path/to/DRfold2",
        "MSA_FILE": "/path/to/msa.a3m",
        "MODEL_WEIGHTS": "/path/to/weights.pt",
    }
```

然后在脚本中使用：

```bash
conda activate ###CONDA_ENV###
python ###ALGO_PATH###/predict.py \
    --msa ###MSA_FILE### \
    --weights ###MODEL_WEIGHTS###
```

## 模板示例

### 基础预测任务

```bash
#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --cpus-per-task=###CPUS###
#SBATCH --mem=###MEM###
#SBATCH --gres=gpu:###GPUS###
#SBATCH --time=###TIME_LIMIT###
#SBATCH --output=###LOG_FILE###

set -e

conda activate ###CONDA_ENV###
cd ###TASK_DIR###

python ###ALGO_PATH###/predict.py \
    --input ###INPUT_FASTA### \
    --output ###OUTPUT_DIR###/model.pdb
```

### 带MSA的预测任务

```bash
#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --gres=gpu:###GPUS###
#SBATCH --output=###LOG_FILE###

set -e

conda activate ###CONDA_ENV###
cd ###TASK_DIR###

python ###ALGO_PATH###/predict.py \
    --fasta ###INPUT_FASTA### \
    --msa ###MSA_FILE### \
    --output ###OUTPUT_DIR###/model.pdb
```

### 多模型生成

```bash
#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --gres=gpu:###GPUS###
#SBATCH --output=###LOG_FILE###

set -e

conda activate ###CONDA_ENV###
cd ###TASK_DIR###

# Generate 5 models with different seeds
for seed in 1 2 3 4 5; do
    python ###ALGO_PATH###/predict.py \
        --input ###INPUT_FASTA### \
        --seed $seed \
        --output ###OUTPUT_DIR###/model_${seed}.pdb
done
```

## 命名规范

建议使用以下命名格式：

- `{algorithm}_{task}.sh` - 例如 `drfold2_predict.sh`
- `{algorithm}_{task}_with_{feature}.sh` - 例如 `nufold_predict_with_msa.sh`

## 注意事项

1. **使用 `set -e`** - 任何命令失败时立即退出
2. **激活conda环境** - 确保使用正确的Python环境
3. **切换到任务目录** - `cd ###TASK_DIR###` 确保相对路径正确
4. **输出到任务目录** - 所有输出文件应保存在 `###OUTPUT_DIR###` 或 `###TASK_DIR###`
5. **添加完成消息** - 脚本结束时 `echo "Task completed"` 便于调试
