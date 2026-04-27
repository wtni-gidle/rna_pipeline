#!/usr/bin/env python3
"""Main entry point for RNA structure prediction pipeline.

Usage:
    # Run all enabled algorithms
    python run_pipeline.py input.fasta H1214

    # Run specific algorithms
    python run_pipeline.py input.fasta H1214 --algorithms DRfold2 RhoFold

    # Submit jobs without waiting
    python run_pipeline.py input.fasta H1214 --no-wait

    # Force rerun (ignore completed tasks)
    python run_pipeline.py input.fasta H1214 --no-resume

    # Local execution (no Slurm)
    python run_pipeline.py input.fasta H1214 --local
"""

import argparse
import sys
from pathlib import Path

import yaml

from rna_pipeline.core import Pipeline, TaskContext


def load_config(config_path: Path) -> dict:
    """Load YAML configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def build_algorithm_from_config(
    algo_config: dict,
    context: TaskContext,
    algorithm_paths: dict
):
    """Dynamically import and build algorithm.

    This is a placeholder - you'll implement actual algorithm builders
    in separate files (e.g., algorithms/drfold2.py).
    """
    algo_name = algo_config["name"]

    # Import algorithm builder dynamically
    try:
        module = __import__(
            f"rna_pipeline.algorithms.{algo_name.lower()}",
            fromlist=["build_algorithm"]
        )
        return module.build_algorithm(context, algo_config, algorithm_paths)
    except ImportError:
        print(f"Warning: Algorithm {algo_name} not implemented yet")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="RNA structure prediction pipeline"
    )
    parser.add_argument(
        "input_fasta",
        type=Path,
        help="Input FASTA file"
    )
    parser.add_argument(
        "target_name",
        help="Target name (used for output directory)"
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output root directory (overrides config)"
    )
    parser.add_argument(
        "-a", "--algorithms",
        nargs="+",
        help="Run only specified algorithms (default: all enabled in config)"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Submit jobs and exit without waiting"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Rerun all tasks (ignore completed markers)"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run locally without Slurm"
    )

    args = parser.parse_args()

    # Validate input
    if not args.input_fasta.exists():
        print(f"Error: Input FASTA not found: {args.input_fasta}")
        return 1

    # Load configuration
    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}")
        return 1

    config = load_config(args.config)

    # Setup output directory
    output_root = args.output or Path(config["output"]["root"])
    output_root = output_root / args.target_name
    output_root.mkdir(parents=True, exist_ok=True)

    # Create pipeline
    slurm_enabled = config["slurm"]["enabled"] and not args.local
    pipeline = Pipeline(
        target_name=args.target_name,
        input_fasta=args.input_fasta,
        output_root=output_root,
        slurm_enabled=slurm_enabled
    )

    # Filter algorithms
    enabled_algos = [
        a for a in config["algorithms"]
        if a.get("enabled", True)
    ]

    if args.algorithms:
        enabled_algos = [
            a for a in enabled_algos
            if a["name"] in args.algorithms
        ]

    if not enabled_algos:
        print("No algorithms to run")
        return 0

    print(f"Running algorithms: {[a['name'] for a in enabled_algos]}")

    # Build and add algorithms
    algorithm_paths = config.get("algorithm_paths", {})

    for algo_config in enabled_algos:
        algo_name = algo_config["name"]
        algo_dir = output_root / algo_name

        context = TaskContext(
            target_name=args.target_name,
            input_fasta=args.input_fasta,
            output_root=output_root,
            algorithm_dir=algo_dir,
            slurm_enabled=slurm_enabled
        )

        algo = build_algorithm_from_config(
            algo_config, context, algorithm_paths
        )

        if algo:
            pipeline.add_algorithm(algo)

    # Run pipeline
    success = pipeline.run(
        resume=not args.no_resume,
        wait=not args.no_wait
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
