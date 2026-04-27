"""Template for implementing a new algorithm.

Copy this file and rename to your algorithm name (e.g., drfold2.py).
"""

from pathlib import Path
from rna_pipeline.core import Task, SlurmTask, Algorithm, TaskContext


# Get template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "slurm_templates"


# ============================================================
# Option 1: Simple single-task algorithm (no MSA needed)
# ============================================================

class MyAlgorithmPredictTask(SlurmTask):
    """Structure prediction task."""

    def __init__(self, context: TaskContext, config: dict, paths: dict):
        # Set path to your Slurm script template
        script_template = TEMPLATE_DIR / "myalgorithm_predict.sh"

        super().__init__(
            name="predict",
            context=context,
            script_template_path=script_template,
            partition=config.get("partition", "gpu"),
            time_limit=config.get("time_limit", "24:00:00"),
            cpus=config.get("cpus", 8),
            mem=config.get("mem", "32G"),
            gpus=config.get("gpus", 1)
        )
        self.conda_env = config.get("conda_env", "myalgo")
        self.algo_path = Path(paths.get("MyAlgorithm", "/path/to/MyAlgorithm"))

    def check_prerequisites(self) -> tuple[bool, str]:
        """Check if prerequisites are met."""
        # Check input FASTA
        if not self.context.input_fasta.exists():
            return False, f"Input FASTA not found: {self.context.input_fasta}"

        # Check algorithm installation
        if not self.algo_path.exists():
            return False, f"Algorithm not found at {self.algo_path}"

        # TODO: Add more checks (conda env, GPU availability, etc.)

        return True, ""

    def is_completed(self) -> bool:
        """Check if output exists and is valid."""
        output_pdb = self.task_dir / "predicted_structure.pdb"

        if not output_pdb.exists():
            return False

        # Validate PDB content
        content = output_pdb.read_text()
        if "ATOM" not in content:
            return False

        # TODO: Add more validation (minimum atoms, valid format, etc.)

        return True

    def get_template_variables(self) -> dict[str, str]:
        """Provide custom variables for ###KEYWORD### replacement in template."""
        return {
            "CONDA_ENV": self.conda_env,
            "ALGO_PATH": str(self.algo_path),
        }


# ============================================================
# Option 2: Multi-task algorithm (MSA + prediction)
# ============================================================

class MyAlgorithmMSATask(Task):
    """MSA generation task (CPU-only, local execution)."""

    def __init__(self, context: TaskContext, config: dict, paths: dict):
        super().__init__("msa", context)
        self.rmsa_path = Path(paths.get("rMSA", "/path/to/rMSA"))

    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.context.input_fasta.exists():
            return False, "Input FASTA not found"

        if not self.rmsa_path.exists():
            return False, f"rMSA not found at {self.rmsa_path}"

        return True, ""

    def is_completed(self) -> bool:
        output_msa = self.task_dir / "output.a3m"
        if not output_msa.exists():
            return False

        # Validate MSA has at least 2 sequences
        lines = output_msa.read_text().strip().split("\n")
        return len(lines) >= 2

    def run(self) -> bool:
        """Run MSA generation locally."""
        import subprocess

        self.mark_running()

        output_msa = self.task_dir / "output.a3m"
        cmd = [
            str(self.rmsa_path / "bin" / "rMSA"),
            "-i", str(self.context.input_fasta),
            "-o", str(output_msa),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.task_dir
        )

        if result.returncode == 0 and self.is_completed():
            self.mark_done()
            return True
        else:
            self.mark_failed()
            print(f"MSA generation failed: {result.stderr}")
            return False


class MyAlgorithmPredictWithMSATask(SlurmTask):
    """Structure prediction task that uses MSA."""

    def __init__(self, context: TaskContext, config: dict, paths: dict, msa_task: Task):
        script_template = TEMPLATE_DIR / "myalgorithm_predict_with_msa.sh"

        super().__init__(
            name="predict",
            context=context,
            script_template_path=script_template,
            partition=config.get("partition", "gpu"),
            gpus=config.get("gpus", 1)
        )
        self.msa_task = msa_task
        self.conda_env = config.get("conda_env", "myalgo")
        self.algo_path = Path(paths.get("MyAlgorithm", "/path/to/MyAlgorithm"))

    def check_prerequisites(self) -> tuple[bool, str]:
        # Check if MSA task is completed
        if not self.msa_task.is_completed():
            return False, "MSA task not completed"

        # Check if MSA file exists
        msa_file = self.msa_task.task_dir / "output.a3m"
        if not msa_file.exists():
            return False, f"MSA file not found: {msa_file}"

        return True, ""

    def is_completed(self) -> bool:
        output_pdb = self.task_dir / "predicted_structure.pdb"
        return output_pdb.exists() and "ATOM" in output_pdb.read_text()

    def get_template_variables(self) -> dict[str, str]:
        """Provide MSA file path and other custom variables."""
        msa_file = self.msa_task.task_dir / "output.a3m"

        return {
            "CONDA_ENV": self.conda_env,
            "ALGO_PATH": str(self.algo_path),
            "MSA_FILE": str(msa_file),
        }


# ============================================================
# Build function (required by framework)
# ============================================================

def build_algorithm(context: TaskContext, config: dict, paths: dict) -> Algorithm:
    """Build algorithm with tasks.

    This function is called by the framework to construct your algorithm.

    Args:
        context: Shared context (input files, output dirs, etc.)
        config: Algorithm-specific config from config.yaml
        paths: Paths to algorithm installations

    Returns:
        Algorithm object with ordered tasks
    """
    # Option 1: Single task (no MSA)
    predict_task = MyAlgorithmPredictTask(context, config, paths)
    return Algorithm(config["name"], [predict_task])

    # Option 2: Multi-task (MSA + prediction)
    # msa_task = MyAlgorithmMSATask(context, config, paths)
    # predict_task = MyAlgorithmPredictWithMSATask(context, config, paths, msa_task)
    # return Algorithm(config["name"], [msa_task, predict_task])
