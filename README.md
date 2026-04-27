# RNA Structure Prediction Pipeline

可扩展的RNA结构预测pipeline框架，支持多种算法、Slurm调度、断点续跑。

## 最简使用（推荐）

不需要打包成 Python 包，直接按源码仓库运行即可。

```bash
# 1) clone
git clone <your-github-repo-url>
cd rna_pipeline

# 2) 安装最小依赖
python -m pip install -r requirements.txt

# 3) 快速验证（本地模式，不依赖 Slurm）
python quickstart.py
```

如果你要跑正式流程入口：

```bash
python run_pipeline.py <input.fasta> <target_name> --local
```

## 设计理念

- **最小化核心**：框架只负责任务调度、状态管理、依赖解析
- **高可扩展性**：添加新算法只需继承`Task`类
- **简单目录结构**：`output/{target}/{algorithm}/{task}/`
- **断点续跑**：通过marker文件（`.done`/`.failed`/`.running`）实现
- **Slurm支持**：自动生成作业脚本并提交

## 目录结构

```
pipeline/
  core.py                 # 核心框架（Task, Algorithm, Pipeline类）
  example_algorithm.py    # 示例：如何实现具体算法
  config.yaml            # 配置文件
  run_pipeline.py        # 主入口
  algorithms/            # 具体算法实现（你负责）
    drfold2.py
    rhofold.py
    nufold.py
    ...
```

## 快速开始

### 1. 创建Slurm脚本模板

在 `slurm_templates/drfold2_predict.sh` 中使用 `###KEYWORD###` 占位符：

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

### 2. 实现算法Python代码

创建 `pipeline/algorithms/drfold2.py`：

```python
from pathlib import Path
from pipeline.core import SlurmTask, Algorithm, TaskContext

TEMPLATE_DIR = Path(__file__).parent.parent / "slurm_templates"

class DRfold2PredictTask(SlurmTask):
    def __init__(self, context, config, paths):
        script_template = TEMPLATE_DIR / "drfold2_predict.sh"
        
        super().__init__(
            "predict", context,
            script_template_path=script_template,
            partition="gpu", gpus=1
        )
        self.conda_env = config.get("conda_env", "drfold2")
        self.algo_path = Path(paths.get("DRfold2"))
    
    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.context.input_fasta.exists():
            return False, "Input FASTA not found"
        return True, ""
    
    def is_completed(self) -> bool:
        output = self.task_dir / "model.pdb"
        return output.exists() and "ATOM" in output.read_text()
    
    def get_template_variables(self) -> dict[str, str]:
        # 提供自定义变量替换 ###KEYWORD###
        return {
            "CONDA_ENV": self.conda_env,
            "ALGO_PATH": str(self.algo_path),
        }

def build_algorithm(context, config, paths):
    task = DRfold2PredictTask(context, config, paths)
    return Algorithm("DRfold2", [task])
```

### 3. 配置算法

编辑 `config.yaml`：

```yaml
algorithms:
  - name: DRfold2
    enabled: true
    conda_env: drfold2
```

### 4. 运行

```bash
# 运行所有启用的算法
python pipeline/run_pipeline.py input.fasta H1214

# 只运行指定算法
python pipeline/run_pipeline.py input.fasta H1214 -a DRfold2 RhoFold

# 提交作业后立即退出（不等待完成）
python pipeline/run_pipeline.py input.fasta H1214 --no-wait

# 本地运行（不使用Slurm）
python pipeline/run_pipeline.py input.fasta H1214 --local
```

## 核心概念

### Task（任务）

最小执行单元，必须实现：

- `check_prerequisites()`: 检查前置条件（输入文件、环境等）
- `is_completed()`: 判断任务是否已完成（输出文件存在且有效）
- `run()`: 执行任务逻辑（Task类）或 `get_template_variables()`: 提供模板变量（SlurmTask类）

两种Task类型：

1. **Task**: 本地执行（如MSA生成），需实现 `run()`
2. **SlurmTask**: 提交到Slurm队列（如GPU预测），需设置 `script_template_path` 和实现 `get_template_variables()`

**SlurmTask使用外部脚本模板**：
- 脚本模板放在 `slurm_templates/` 目录
- 使用 `###KEYWORD###` 作为占位符
- 框架自动替换为实际值

### Algorithm（算法）

包含多个有序的Task，按顺序执行。例如：

```python
# NuFold需要先生成MSA，再预测结构
msa_task = RMSATask("msa", context)
predict_task = NuFoldPredictTask(context, msa_task)
algo = Algorithm("NuFold", [msa_task, predict_task])
```

### Pipeline（流水线）

管理多个Algorithm的执行，支持：

- 并行运行多个算法（各自独立）
- 断点续跑（`resume=True`）
- 等待Slurm作业完成（`wait=True`）

## 状态管理

每个Task目录下有marker文件：

- `.done`: 任务成功完成
- `.failed`: 任务失败
- `.running`: 任务正在运行

框架根据这些文件判断是否需要重新运行。

## 输出目录结构

```
output/
  H1214/                    # target_name
    DRfold2/
      .done                 # 算法完成标记
      predict/
        .done               # 任务完成标记
        predict.sh          # Slurm脚本
        predict.log         # 日志
        model.pdb           # 输出
    RhoFold/
      predict/
        ...
    NuFold/
      msa/
        output.a3m
      predict/
        model.pdb
```

## 任务依赖

如果Task B依赖Task A的输出，在`check_prerequisites()`中检查：

```python
class PredictTask(SlurmTask):
    def __init__(self, context, msa_task):
        super().__init__("predict", context)
        self.msa_task = msa_task
    
    def check_prerequisites(self):
        # 检查MSA任务是否完成
        if not self.msa_task.is_completed():
            return False, "MSA not ready"
        
        msa_file = self.msa_task.task_dir / "output.a3m"
        if not msa_file.exists():
            return False, "MSA file not found"
        
        return True, ""
```

## 扩展指南

### 添加新算法

1. 创建 `pipeline/algorithms/{algorithm_name}.py`
2. 实现Task类（继承`Task`或`SlurmTask`）
3. 实现 `build_algorithm(context, config, paths)` 函数
4. 在 `config.yaml` 中添加配置

### 自定义Slurm参数和模板变量

```python
class MyTask(SlurmTask):
    def __init__(self, context):
        script_template = TEMPLATE_DIR / "my_script.sh"
        
        super().__init__(
            name="my_task",
            context=context,
            script_template_path=script_template,
            partition="gpu",      # 分区
            time_limit="48:00:00", # 时间限制
            cpus=16,              # CPU核心数
            mem="64G",            # 内存
            gpus=2                # GPU数量
        )
    
    def get_template_variables(self) -> dict[str, str]:
        # 自定义变量会替换脚本中的 ###KEYWORD###
        return {
            "MY_CUSTOM_VAR": "value",
            "ANOTHER_VAR": "/path/to/something",
        }
```

**默认可用的模板变量**（无需在 `get_template_variables()` 中提供）：
- `###JOB_NAME###`, `###PARTITION###`, `###CPUS###`, `###MEM###`, `###GPUS###`
- `###TIME_LIMIT###`, `###LOG_FILE###`
- `###INPUT_FASTA###`, `###OUTPUT_DIR###`, `###TASK_DIR###`

### 本地执行（无Slurm）

设置 `context.slurm_enabled = False`，SlurmTask会自动降级为本地执行。

## 注意事项

1. **路径配置**：修改 `config.yaml` 中的 `algorithm_paths` 和 `output.root`
2. **Conda环境**：确保每个算法的conda环境已创建
3. **前置检查**：在 `check_prerequisites()` 中充分检查，避免提交后失败
4. **输出验证**：在 `is_completed()` 中验证输出文件内容，不只是检查存在性
5. **日志文件**：Slurm日志在 `{task_dir}/{task_name}.log`

## 与参考代码的对比

| 特性 | 参考代码 (AF3) | 本框架 |
|------|---------------|--------|
| 任务粒度 | 单个MSA任务 | 任意Task组合 |
| 算法支持 | 单一算法 | 多算法并行 |
| 依赖管理 | 无 | Task间依赖 |
| 扩展性 | 硬编码 | 继承+配置 |
| 代码量 | ~800行 | ~300行核心 |

## 下一步

你需要实现具体算法：

1. `pipeline/algorithms/drfold2.py`
2. `pipeline/algorithms/rhofold.py`
3. `pipeline/algorithms/nufold.py`
4. ...

参考 `example_algorithm.py` 中的模式即可。
