# RNA Structure Prediction Pipeline - 完整框架

## 框架已完成 ✓

一个最小化、高可扩展的RNA结构预测pipeline框架，支持：
- ✓ Slurm作业调度
- ✓ 断点续跑
- ✓ 外部脚本模板（`###KEYWORD###` 占位符）
- ✓ 任务依赖管理
- ✓ 简单目录结构

## 文件结构

```
pipeline/
├── README.md                    # 详细文档
├── SUMMARY.md                   # 快速总结
├── __init__.py                  # Package初始化
├── core.py                      # 核心框架 (~250行)
│   ├── Task                     # 任务基类
│   ├── SlurmTask               # Slurm任务类
│   ├── Algorithm               # 算法容器
│   └── Pipeline                # 流水线管理器
│
├── config.yaml                  # 配置文件模板
├── run_pipeline.py             # 主入口脚本
├── quickstart.py               # 快速测试示例
├── example_algorithm.py        # 完整实现示例
│
├── algorithms/                  # 算法实现目录（你负责填充）
│   ├── __init__.py
│   └── template.py             # 实现模板
│       ├── 单任务算法示例
│       ├── 多任务算法示例（MSA + predict）
│       └── build_algorithm()函数
│
└── slurm_templates/            # Slurm脚本模板目录（你负责填充）
    ├── README.md               # 模板变量说明
    ├── template_predict.sh     # 通用模板
    ├── drfold2_predict.sh      # DRfold2示例
    └── nufold_predict.sh       # NuFold示例
```

## 核心设计

### 1. 外部脚本模板系统

**不再硬编码Slurm脚本**，而是使用外部模板文件：

```bash
# slurm_templates/drfold2_predict.sh
#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --gres=gpu:###GPUS###

conda activate ###CONDA_ENV###
python ###ALGO_PATH###/predict.py \
    --input ###INPUT_FASTA### \
    --output ###OUTPUT_DIR###/model.pdb
```

### 2. Python实现只需提供变量

```python
class DRfold2Task(SlurmTask):
    def __init__(self, context, config, paths):
        script_template = TEMPLATE_DIR / "drfold2_predict.sh"
        super().__init__("predict", context, 
                        script_template_path=script_template)
        self.conda_env = config["conda_env"]
        self.algo_path = paths["DRfold2"]
    
    def get_template_variables(self):
        return {
            "CONDA_ENV": self.conda_env,
            "ALGO_PATH": str(self.algo_path),
        }
```

### 3. 默认变量自动提供

框架自动提供这些变量，无需手动定义：
- `###JOB_NAME###`, `###PARTITION###`, `###CPUS###`, `###MEM###`, `###GPUS###`
- `###TIME_LIMIT###`, `###LOG_FILE###`
- `###INPUT_FASTA###`, `###OUTPUT_DIR###`, `###TASK_DIR###`

## 你需要做什么

### 为每个RNA算法创建两个文件：

1. **Slurm脚本模板** (`slurm_templates/{algorithm}_{task}.sh`)
2. **Python实现** (`algorithms/{algorithm}.py`)

### 需要实现的算法（根据CLAUDE.md）

| 算法 | 任务 | 优先级 |
|------|------|--------|
| DRfold2 | predict | 高（最简单） |
| RhoFold+ | predict | 高 |
| trRosettaRNA2 | predict (可选msa) | 中 |
| NuFold | msa → predict | 中 |
| trRosettaRNA v1.1 | msa → predict | 低 |
| DeepFoldRNA | msa → predict | 低 |
| RoseTTAFold2NA | msa → predict | 低 |

## 快速开始

### 1. 测试框架

```bash
cd /home/nwt/projects/rna_program/pipeline
python quickstart.py
```

### 2. 实现第一个算法（建议DRfold2）

```bash
# 创建脚本模板
vim slurm_templates/drfold2_predict.sh

# 创建Python实现
vim algorithms/drfold2.py

# 修改配置
vim config.yaml
```

### 3. 运行

```bash
python run_pipeline.py input.fasta H1214 -a DRfold2
```

## 关键优势

✓ **易于修改** - 直接编辑Slurm脚本，无需改Python代码  
✓ **最小代码** - 核心框架仅250行  
✓ **清晰分离** - 脚本模板 vs Python逻辑  
✓ **可扩展** - 添加算法只需两个文件  
✓ **断点续跑** - 自动识别已完成任务  
✓ **依赖管理** - Task间可声明依赖  

## 文档

- **README.md** - 完整使用文档
- **SUMMARY.md** - 快速参考
- **slurm_templates/README.md** - 模板变量说明
- **example_algorithm.py** - 完整示例代码
- **algorithms/template.py** - 实现模板

## 输出目录结构

```
output/
  {target_name}/
    DRfold2/
      .done                 # 算法完成标记
      predict/
        .done               # 任务完成标记
        predict.sh          # 生成的Slurm脚本
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

## 下一步

1. 阅读 `README.md` 了解详细设计
2. 查看 `example_algorithm.py` 学习实现模式
3. 参考 `algorithms/template.py` 开始实现
4. 从最简单的算法开始（DRfold2或RhoFold+）
5. 逐步添加其他算法

---

**框架已完成，现在轮到你实现具体算法了！** 🚀
