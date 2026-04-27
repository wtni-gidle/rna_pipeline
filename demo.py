"""Example: How to implement algorithms using external Slurm script templates.

This shows the new pattern with ###KEYWORD### placeholders.
"""

from pathlib import Path
from rna_pipeline.core import Task, SlurmTask, Algorithm, TaskContext


# Get template directory
TEMPLATE_DIR = Path(__file__).parent / "slurm_templates"


# ============================================================
# Example 1: Simple task with script template
# ============================================================

class DRfold2PredictTask(SlurmTask):
    """Run DRfold2 structure prediction using external script template."""

    def __init__(self, context: TaskContext, conda_env: str, algo_path: Path):
        # Set script template path
        script_template = TEMPLATE_DIR / "drfold2_predict.sh"

        super().__init__(
            name="predict",
            context=context,
            script_template_path=script_template,
            partition="gpu",
            time_limit="12:00:00",
            cpus=8,
            mem="32G",
            gpus=1
        )
        self.conda_env = conda_env
        self.algo_path = algo_path

    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.context.input_fasta.exists():
            return False, f"Input FASTA not found: {self.context.input_fasta}"

        if not self.algo_path.exists():
            return False, f"Algorithm not found at {self.algo_path}"

        return True, ""

    def is_completed(self) -> bool:
        output_pdb = self.task_dir / "predicted_structure.pdb"
        if not output_pdb.exists():
            return False

        content = output_pdb.read_text()
        return "ATOM" in content

    def get_template_variables(self) -> dict[str, str]:
        """Provide custom variables for template replacement."""
        return {
            "CONDA_ENV": self.conda_env,
            "ALGO_PATH": str(self.algo_path),
        }


# ============================================================
# Example 2: Task with dependency and custom variables
# ============================================================

class RMSATask(SlurmTask):
    """Generate MSA using rMSA on Slurm."""

    def __init__(self, context: TaskContext):
        script_template = TEMPLATE_DIR / "run_rmsa.sh"

        super().__init__(
            name="rmsa",
            context=context,
            script_template_path=script_template,
            server="hpc6",
            partition="cpu",
            account="...",
            cpus=16,
            mem="64G",
            time_limit="06:00:00",
        )

    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.context.input_fasta.exists():
            return False, "Input FASTA not found"

        return True, ""

    def is_completed(self) -> bool:
        output_msa = self.task_dir / "seq.afa"
        if not output_msa.exists():
            return False

        lines = output_msa.read_text().strip().split("\n")
        return len(lines) >= 2

    # todo
    def get_template_variables(self) -> dict[str, str]:
        return {
            "INPUT_FASTA": str(self.context.input_fasta),
            "OUTPUT_DIR": str(self.task_dir),
        }


class NuFoldPredictTask(SlurmTask):
    """NuFold prediction that requires MSA from previous task."""

    def __init__(self, context: TaskContext, msa_task: Task):
        script_template = TEMPLATE_DIR / "run_nufold_predict.sh"

        super().__init__(
            name="nufold_predict",
            context=context,
            script_template_path=script_template,
            server="hpc6",
            partition="gpu",
            account="...",
            cpus=16,
            mem="64G",
            time_limit="06:00:00",
        )
        self.msa_task = msa_task
    
    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.msa_task.is_completed():
            return False, f"MSA task not completed: {self.msa_task.name}"
        
        a3m_file = self.output_dir / "seq.a3m"
        if not a3m_file.exists():
            # nufold/default/seq/seq.a3m -> rmsa/default/seq/seq.afa
            a3m_file.symlink_to(self.msa_task.output_dir / "seq.afa")

        return True, ""

    # todo
    def is_completed(self) -> bool:
        output_pdb = self.task_dir / "model.pdb"
        return output_pdb.exists() and "ATOM" in output_pdb.read_text()

    # todo
    def get_template_variables(self) -> dict[str, str]:
        """Provide MSA file path and other custom variables."""
        msa_file = self.msa_task.task_dir / "output.a3m"

        return {
            "INPUT_FASTA": "",
            "OUTPUT_DIR": str(self.task_dir / "seq"),
            "NUM_SEEDS": "",
            "RANK": ""
        }


# ============================================================
# Build complete algorithms
# ============================================================

def build_drfold2_algorithm(context: TaskContext, config: dict, paths: dict) -> Algorithm:
    """DRfold2: single prediction task (no MSA needed)."""
    predict_task = DRfold2PredictTask(
        context=context,
        conda_env=config.get("conda_env", "drfold2"),
        algo_path=Path(paths.get("DRfold2", "/path/to/DRfold2"))
    )
    return Algorithm("DRfold2", [predict_task])


def build_nufold_algorithm(context: TaskContext, config: dict, paths: dict) -> Algorithm:
    """NuFold: MSA generation → structure prediction."""
    msa_task = RMSATask(
        context=context,
        rmsa_path=Path(paths.get("rMSA", "/path/to/rMSA"))
    )

    predict_task = NuFoldPredictTask(
        context=context,
        msa_task=msa_task,
        conda_env=config.get("conda_env", "nufold"),
        algo_path=Path(paths.get("NuFold", "/path/to/NuFold"))
    )

    return Algorithm("NuFold", [msa_task, predict_task])


# ============================================================
# Usage example
# ============================================================

if __name__ == "__main__":
    from rna_pipeline.core import Pipeline

    target_name = "H1214"
    input_fasta = Path("/path/to/H1214.fasta")
    output_root = Path("/path/to/output")

    pipeline = Pipeline(
        target_name=target_name,
        input_fasta=input_fasta,
        output_root=output_root,
        slurm_enabled=True
    )

    # Add algorithms
    for algo_name in ["DRfold2", "NuFold"]:
        algo_output_dir = output_root / target_name / algo_name
        context = TaskContext(
            target_name=target_name,
            input_fasta=input_fasta,
            output_root=output_root,
            algorithm_dir=algo_output_dir,
            slurm_enabled=True
        )

        config = {"conda_env": algo_name.lower()}
        paths = {
            "DRfold2": "/path/to/DRfold2",
            "NuFold": "/path/to/NuFold",
            "rMSA": "/path/to/rMSA",
        }

        if algo_name == "DRfold2":
            algo = build_drfold2_algorithm(context, config, paths)
        elif algo_name == "NuFold":
            algo = build_nufold_algorithm(context, config, paths)
        else:
            continue

        pipeline.add_algorithm(algo)

    # Run pipeline
    pipeline.run(resume=True, wait=False)
