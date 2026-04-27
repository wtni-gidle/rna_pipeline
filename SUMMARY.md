# Pipeline Framework Summary

## 已创建的文件

```
pipeline/
├── __init__.py              # Package init
├── core.py                  # 核心框架 (~250行)
├── config.yaml              # 配置文件模板
├── run_pipeline.py          # 主入口
├── example_algorithm.py     # 完整示例
├── quickstart.py            # 快速开始示例
├── README.md                # 详细文档
├── SUMMARY.md               # 本文件
├── algorithms/              # 算法实现（你负责）
│   ├── __init__.py
│   └── template.py          # 算法实现模板
└── slurm_templates/         # Slurm脚本模板（你负责）
    ├── template_predict.sh  # 通用模板
    ├── drfold2_predict.sh   # 示例
    └── nufold_predict.sh    # 示例
```

## 核心类

### 1. Task (基类)
- `check_prerequisites()` - 检查前置条件
- `is_completed()` - 判断是否完成
- `run()` - 执行任务（仅Task类需要）
- 状态管理：`.done` / `.failed` / `.running` marker文件

### 2. SlurmTask (继承Task)
- `script_template_path` - Slurm脚本模板路径
- `get_template_variables()` - 返回模板变量字典
- 自动读取模板、替换 `###KEYWORD###`、提交作业
- 支持本地执行降级

### 3. Algorithm
- 包含多个有序Task
- 按顺序执行，支持断点续跑

### 4. Pipeline
- 管理多个Algorithm
- 并行运行各算法

## 你需要做的

### 为每个RNA算法创建两个文件

**1. Slurm脚本模板** (`slurm_templates/drfold2_predict.sh`):

```bash
#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --gres=gpu:###GPUS###
#SBATCH --output=###LOG_FILE###

conda activate ###CONDA_ENV###
cd ###TASK_DIR###

python ###ALGO_PATH###/predict.py \
    --input ###INPUT_FASTA### \
    --output ###OUTPUT_DIR###/model.pdb
```

**2. Python实现** (`pipeline/algorithms/drfold2.py`):

```python
from pathlib import Path
from pipeline.core import SlurmTask, Algorithm, TaskContext

TEMPLATE_DIR = Path(__file__).parent.parent / "slurm_templates"

class DRfold2PredictTask(SlurmTask):
    def __init__(self, context, config, paths):
        script_template = TEMPLATE_DIR / "drfold2_predict.sh"
        super().__init__("predict", context, 
                        script_template_path=script_template,
                        partition="gpu", gpus=1)
        self.conda_env = config["conda_env"]
        self.algo_path = Path(paths["DRfold2"])
    
    def check_prerequisites(self):
        return True, ""
    
    def is_completed(self):
        return (self.task_dir / "model.pdb").exists()
    
    def get_template_variables(self):
        return {
            "CONDA_ENV": self.conda_env,
            "ALGO_PATH": str(self.algo_path),
        }

def build_algorithm(context, config, paths):
    task = DRfold2PredictTask(context, config, paths)
    return Algorithm("DRfold2", [task])
```

### 需要实现的算法

根据 `CLAUDE.md`，你需要实现：

1. **DRfold2** - 单任务（predict）
2. **RhoFold+** - 单任务（predict）
3. **NuFold** - 两任务（msa → predict）
4. **trRosettaRNA2** - 单或两任务（可选msa → predict）
5. **trRosettaRNA v1.1** - 两任务（msa → predict）
6. **DeepFoldRNA** - 两任务（msa → predict）
7. **RoseTTAFold2NA** - 两任务（msa → predict）

## 使用方式

### 方式1：使用主入口（推荐）

```bash
# 1. 修改 config.yaml 配置路径和算法
# 2. 实现各算法的 algorithms/{name}.py
# 3. 运行
python pipeline/run_pipeline.py input.fasta H1214
```

### 方式2：直接使用框架

```python
from pipeline import Pipeline, TaskContext, Algorithm
from pipeline.algorithms.drfold2 import build_algorithm

pipeline = Pipeline("H1214", Path("input.fasta"), Path("output"))
context = TaskContext(...)
algo = build_algorithm(context, config, paths)
pipeline.add_algorithm(algo)
pipeline.run()
```

### 方式3：快速测试

```bash
python pipeline/quickstart.py
```

## 关键特性

✓ **最小化代码** - 核心框架仅250行  
✓ **高可扩展** - 添加算法只需创建脚本模板+Python类  
✓ **断点续跑** - 通过marker文件自动识别  
✓ **Slurm支持** - 外部脚本模板，使用 `###KEYWORD###` 占位符  
✓ **依赖管理** - Task间可声明依赖关系  
✓ **简单目录** - `output/{target}/{algo}/{task}/`  
✓ **易于修改** - 直接编辑Slurm脚本，无需改Python代码  

## 下一步

1. 测试框架：`python pipeline/quickstart.py`
2. 修改 `config.yaml` 中的路径
3. 参考 `template.py` 实现第一个算法（建议从DRfold2开始）
4. 逐步添加其他算法

## 疑问？

- 看 `README.md` 了解详细设计
- 看 `example_algorithm.py` 了解完整示例
- 看 `template.py` 作为实现起点
