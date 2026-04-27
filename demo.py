"""Example: How to implement algorithms using external Slurm script templates.

This shows the new pattern with ###KEYWORD### placeholders.
"""

from pathlib import Path
from rna_pipeline.core import Task, SlurmTask, Algorithm


# Get template directory
TEMPLATE_DIR = Path(__file__).parent / "slurm_templates"


# ============================================================
# Example 1: Simple task with script template
# ============================================================

class DRfold2PredictTask(SlurmTask):
    """Run DRfold2 structure prediction using external script template."""

    def __init__(self, conda_env: str, algo_path: Path):
        # Set script template path
        script_template = TEMPLATE_DIR / "drfold2_predict.sh"

        super().__init__(
            name="predict",
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

    def __init__(self, algorithm_dir: Path, version: str, input_fasta: Path):
        script_template = TEMPLATE_DIR / "run_rmsa.sh"

        super().__init__(
            name="rmsa",
            algorithm_dir=algorithm_dir,
            version=version,
            input_fasta=input_fasta,
            script_template_path=script_template,
            server="hpc6",
            partition="cp11",
            account="...",
            cpus=16,
            mem="64G",
            time_limit="06:00:00",
        )

    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.input_fasta.exists():
            return False, "Input FASTA not found"

        return True, ""

    def is_completed(self) -> bool:
        output_msa = self.seq_dir / "seq.afa"
        if not output_msa.exists():
            return False

        lines = output_msa.read_text().strip().split("\n")
        return len(lines) >= 2

    # todo
    def get_template_variables(self) -> dict[str, str]:
        return {
            "INPUT_FASTA": str(self.input_fasta),
            "OUTPUT_DIR": str(self.seq_dir),
        }


class NuFoldPredictTask(SlurmTask):
    """NuFold prediction that requires MSA from previous task."""

    def __init__(self, msa_task: Task, algorithm_dir: Path, version: str, input_fasta: Path):
        script_template = TEMPLATE_DIR / "run_nufold_predict.sh"

        super().__init__(
            name="nufold_predict",
            algorithm_dir=algorithm_dir,
            version=version,
            input_fasta=input_fasta,
            script_template_path=script_template,
            server="hpc6",
            partition="5090",
            account="...",
            cpus=16,
            mem="64G",
            time_limit="06:00:00",
        )
        self.msa_task = msa_task
    
    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.msa_task.is_completed():
            return False, f"MSA task not completed: {self.msa_task.name}"
        
        a3m_file = self.seq_dir / "seq.a3m"
        if not a3m_file.exists():
            # nufold/default/seq/seq.a3m -> rmsa/default/seq/seq.afa
            a3m_file.symlink_to(self.msa_task.seq_dir / "seq.afa")

        return True, ""

    # todo
    def is_completed(self) -> bool:
        output_pdb = self.seq_dir.glob("seq_*.pdb")
        return any(output_pdb)

    # todo
    def get_template_variables(self) -> dict[str, str]:
        """Provide MSA file path and other custom variables."""
        return {
            "INPUT_FASTA": str(self.input_fasta),
            "OUTPUT_DIR": str(self.seq_dir),
            "NUM_SEEDS": "5",
            "RANK": "false"
        }


# ============================================================
# Build complete algorithms
# ============================================================


def build_nufold_algorithm(target_dir: Path, version: str) -> Algorithm:
    """NuFold: MSA generation → structure prediction."""
    msa_task = RMSATask(
        algorithm_dir=target_dir / "rmsa",
        version=version,
        input_fasta=target_dir / "seq.fasta"
    )

    predict_task = NuFoldPredictTask(
        algorithm_dir=target_dir / "nufold",
        version=version,
        input_fasta=target_dir / "seq.fasta",
        msa_task=msa_task
    )

    return Algorithm("NuFold", [msa_task, predict_task])


# ============================================================
# Usage example
# ============================================================

if __name__ == "__main__":
    from rna_pipeline.core import Pipeline

    target_name = "R1260"
    output_root = Path("/fs6/home/casp_2026/bio-home/nwt/CASP17_rna")
    target_dir = output_root / target_name

    # pipeline = Pipeline(
    #     target_name=target_name,
    #     input_fasta=seq_path,
    #     output_root=output_root,
    #     slurm_enabled=True
    # )
    # # Run pipeline
    # pipeline.run(resume=True, wait=False)

    build_nufold_algorithm(target_dir, version="default")
