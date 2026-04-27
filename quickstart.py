#!/usr/bin/env python3
"""Quick start example: Run DRfold2 on a test sequence."""

from pathlib import Path
from rna_pipeline.core import Pipeline, TaskContext, Algorithm, SlurmTask


class DRfold2Task(SlurmTask):
    """Minimal DRfold2 implementation for testing."""

    def __init__(self, context: TaskContext):
        # Create inline template for testing
        template_path = context.algorithm_dir / "test_template.sh"
        template_path.parent.mkdir(parents=True, exist_ok=True)

        # Write test template
        template_path.write_text("""#!/bin/bash
#SBATCH --job-name=###JOB_NAME###
#SBATCH --partition=###PARTITION###
#SBATCH --gres=gpu:###GPUS###
#SBATCH --cpus-per-task=###CPUS###
#SBATCH --mem=###MEM###
#SBATCH --time=###TIME_LIMIT###
#SBATCH --output=###LOG_FILE###

set -e

echo "Running DRfold2 prediction..."
echo "Input: ###INPUT_FASTA###"
echo "Output: ###OUTPUT_DIR###/output.pdb"

# For testing, create dummy output
touch ###OUTPUT_DIR###/output.pdb
echo "ATOM      1  N   ALA A   1       0.000   0.000   0.000" >> ###OUTPUT_DIR###/output.pdb

echo "Done"
""")

        super().__init__(
            name="predict",
            context=context,
            script_template_path=template_path,
            partition="gpu",
            gpus=1,
            cpus=8,
            mem="32G",
            time_limit="12:00:00"
        )

    def check_prerequisites(self) -> tuple[bool, str]:
        if not self.context.input_fasta.exists():
            return False, "Input FASTA not found"
        return True, ""

    def is_completed(self) -> bool:
        output = self.task_dir / "output.pdb"
        return output.exists()

    def get_template_variables(self) -> dict[str, str]:
        # No custom variables needed for this test
        return {}


def main():
    # Setup
    target_name = "test_target"
    input_fasta = Path("test_input.fasta")
    output_root = Path("test_output")

    # Create test input if not exists
    if not input_fasta.exists():
        input_fasta.write_text(">test_sequence\nGGGGAAAACCCC\n")
        print(f"Created test input: {input_fasta}")

    # Create pipeline
    pipeline = Pipeline(
        target_name=target_name,
        input_fasta=input_fasta,
        output_root=output_root,
        slurm_enabled=True  # Set to False for local testing
    )

    # Create algorithm
    context = TaskContext(
        target_name=target_name,
        input_fasta=input_fasta,
        output_root=output_root,
        algorithm_dir=output_root / target_name / "DRfold2",
        slurm_enabled=True
    )

    task = DRfold2Task(context)
    algorithm = Algorithm("DRfold2", [task])
    pipeline.add_algorithm(algorithm)

    # Run
    print("\n" + "="*60)
    print("Quick Start Example")
    print("="*60)
    print(f"Input: {input_fasta}")
    print(f"Output: {output_root}/{target_name}/DRfold2/predict/")
    print("="*60 + "\n")

    success = pipeline.run(resume=True, wait=False)

    if success:
        print("\n✓ Pipeline submitted successfully")
        print(f"\nCheck status:")
        print(f"  - Output dir: {output_root}/{target_name}/DRfold2/predict/")
        print(f"  - Log file: {output_root}/{target_name}/DRfold2/predict/predict.log")
        print(f"  - Job script: {output_root}/{target_name}/DRfold2/predict/predict.sh")
    else:
        print("\n✗ Pipeline failed")

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
