"""RNA structure prediction pipeline core framework.

Minimal, extensible framework for running RNA prediction algorithms with:
- Slurm job scheduling support
- Checkpoint/resume via marker files
- Per-algorithm task dependencies
- Simple directory structure
"""

from __future__ import annotations

import abc
import pathlib
import subprocess
import time


# Status markers
MARKER_DONE = ".done"
MARKER_FAILED = ".failed"
MARKER_RUNNING = ".running"


class Task(abc.ABC):
    """Base class for pipeline tasks.

    Users implement:
    - check_prerequisites(): Verify inputs/environment
    - is_completed(): Check if output exists and is valid
    - run(): Execute the task
    """

    def __init__(self, name: str, algorithm_dir: pathlib.Path, version: str,
                 input_fasta: pathlib.Path, slurm_enabled: bool = True):
        self.name = name
        self.algorithm_dir = algorithm_dir
        self.version = version
        self.task_dir = algorithm_dir / version # alphafold3/default
        self.input_fasta = input_fasta
        self.slurm_enabled = slurm_enabled
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.seq_dir = self.task_dir / "seq" # alphafold3/default/seq
        self.seq_dir.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    def check_prerequisites(self) -> tuple[bool, str]:
        """Check if prerequisites are met.

        Returns:
            (success, error_message)
        """
        pass

    @abc.abstractmethod
    def is_completed(self) -> bool:
        """Check if task output exists and is valid."""
        pass

    @abc.abstractmethod
    def run(self) -> bool:
        """Execute the task.

        Returns:
            True if successful, False otherwise
        """
        pass

    # Marker file helpers
    def _marker_path(self, marker: str) -> pathlib.Path:
        return self.task_dir / marker

    def mark_running(self):
        self._marker_path(MARKER_RUNNING).touch()
        self._marker_path(MARKER_DONE).unlink(missing_ok=True)
        self._marker_path(MARKER_FAILED).unlink(missing_ok=True)

    def mark_done(self):
        self._marker_path(MARKER_DONE).touch()
        self._marker_path(MARKER_RUNNING).unlink(missing_ok=True)
        self._marker_path(MARKER_FAILED).unlink(missing_ok=True)

    def mark_failed(self):
        self._marker_path(MARKER_FAILED).touch()
        self._marker_path(MARKER_RUNNING).unlink(missing_ok=True)

    def get_status(self) -> str:
        """Get current task status from markers."""
        if self._marker_path(MARKER_DONE).exists():
            return "completed"
        if self._marker_path(MARKER_FAILED).exists():
            return "failed"
        if self._marker_path(MARKER_RUNNING).exists():
            return "running"
        return "ready"


class SlurmTask(Task):
    """Task that submits a Slurm job.

    Users implement:
    - get_template_variables(): Return dict of variables to replace in template
    - is_completed(): Check output validity

    Users set:
    - script_template_path: Path to Slurm script template with ###KEYWORD### placeholders
    """

    def __init__(self, name: str, algorithm_dir: pathlib.Path, version: str,
                 input_fasta: pathlib.Path, slurm_enabled: bool = True,
                 script_template_path: pathlib.Path | None = None, server: str = "hpc6",
                 partition: str = "gpu", time_limit: str = "24:00:00",
                 cpus: int = 8, mem: str = "32G", account: str | None = None,
                 target_name: str | None = None):
        super().__init__(name, algorithm_dir, version, input_fasta, slurm_enabled)
        self.script_template_path = script_template_path
        self.server = server
        self.partition = partition
        self.time_limit = time_limit
        self.cpus = cpus
        self.mem = mem
        self.account = account
        self.target_name = target_name or algorithm_dir.parent.name
        self.job_name = f"{name}_{self.target_name}"
        self.job_script = self.task_dir / f"{name}.sh"
        self.log_file = self.task_dir / f"{name}.log"

    def get_template_variables(self) -> dict[str, str]:
        """Return variables to replace in script template.

        Override this to provide custom variables.
        Default variables are always available:
        - JOB_NAME, PARTITION, CPUS, MEM, GPUS, TIME_LIMIT, LOG_FILE
        - INPUT_FASTA, OUTPUT_DIR, TASK_DIR
        """
        return {}

    def generate_slurm_script(self) -> str:
        """Generate script by reading template and replacing ###KEYWORD### placeholders."""
        if self.script_template_path is None:
            raise ValueError(f"script_template_path not set for {self.name}")

        if not self.script_template_path.exists():
            raise FileNotFoundError(f"Script template not found: {self.script_template_path}")

        # Read template
        template = self.script_template_path.read_text()

        # Default variables
        variables = {
            "SERVER": self.server,
            "JOB_NAME": self.job_name,
            "PARTITION": self.partition,
            "NCPU": str(self.cpus),
            "MEM": self.mem,
            "TIME_LIMIT": self.time_limit,
            "OE_FILE": str(self.log_file),
            "ACCOUNT": self.account or "...",
        }

        # Add user variables
        variables.update(self.get_template_variables())

        # Replace placeholders
        for key, value in variables.items():
            template = template.replace(f"###{key}###", value)

        return template

    def run(self) -> bool:
        """Submit Slurm job and return immediately."""
        if not self.slurm_enabled:
            # Local execution fallback
            return self._run_local()

        # Check if job already in queue
        existing_job_id = self.get_job_id()
        if existing_job_id:
            print(f"[{self.name}] Job {existing_job_id} already in queue, skipping")
            return True

        # Generate and write job script
        script_content = self.generate_slurm_script()
        self.job_script.write_text(script_content)
        self.job_script.chmod(0o755)

        # Submit to Slurm
        self.mark_running()
        result = subprocess.run(
            ["sbatch", str(self.job_script)],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"[{self.name}] sbatch failed: {result.stderr}")
            self.mark_failed()
            return False

        # Extract job ID
        job_id = result.stdout.strip().split()[-1]
        print(f"[{self.name}] Submitted job {job_id}")
        return True

    def _run_local(self) -> bool:
        """Fallback: run script locally (for testing)."""
        script_content = self.generate_slurm_script()
        # Extract commands after #SBATCH directives
        commands = "\n".join(
            line for line in script_content.split("\n")
            if not line.startswith("#SBATCH") and line.strip()
        )

        self.mark_running()
        with open(self.log_file, "w") as f:
            result = subprocess.run(
                commands, shell=True, cwd=self.task_dir,
                stdout=f,
                stderr=subprocess.STDOUT
            )

        if result.returncode == 0 and self.is_completed():
            self.mark_done()
            return True
        else:
            self.mark_failed()
            return False

    def get_job_id(self) -> str | None:
        """Get Slurm job ID if running."""
        result = subprocess.run(
            ["squeue", "-h", "-o", "%A", "-n", self.job_name],
            capture_output=True, text=True
        )
        job_ids = result.stdout.strip().split()
        return job_ids[0] if job_ids else None

    def wait_for_completion(self, poll_interval: int = 60) -> bool:
        """Poll until job completes."""
        while True:
            job_id = self.get_job_id()
            if job_id is None:
                # Job finished
                if self.is_completed():
                    self.mark_done()
                    return True
                else:
                    self.mark_failed()
                    return False

            print(f"[{self.name}] Job {job_id} still running...")
            time.sleep(poll_interval)


class Algorithm:
    """Represents a prediction algorithm with ordered tasks."""

    def __init__(self, name: str, tasks: list[Task]):
        self.name = name
        self.tasks = tasks

    def run(self, resume: bool = True) -> bool:
        """Execute all tasks in order.

        Args:
            resume: Skip completed tasks if True

        Returns:
            True if all tasks succeeded
        """
        print(f"\n{'='*60}")
        print(f"Running algorithm: {self.name}")
        print(f"{'='*60}")

        for task in self.tasks:
            status = task.get_status()

            # Skip if already completed and resume enabled
            if resume and status == "completed":
                print(f"[{task.name}] Already completed, skipping")
                continue

            # Check prerequisites
            ok, error = task.check_prerequisites()
            if not ok:
                print(f"[{task.name}] Prerequisites failed: {error}")
                return False

            # Run task
            print(f"[{task.name}] Starting...")
            success = task.run()

            if not success:
                print(f"[{task.name}] Failed")
                return False

            # For Slurm tasks, optionally wait
            if isinstance(task, SlurmTask) and task.slurm_enabled:
                print(f"[{task.name}] Submitted to Slurm")
                # Don't wait here - let user decide via wait_all()
            else:
                if task.is_completed():
                    task.mark_done()
                    print(f"[{task.name}] Completed")
                else:
                    task.mark_failed()
                    print(f"[{task.name}] Failed validation")
                    return False

        return True

    def wait_all(self, poll_interval: int = 60) -> bool:
        """Wait for all Slurm tasks to complete."""
        slurm_tasks = [t for t in self.tasks if isinstance(t, SlurmTask)]
        if not slurm_tasks:
            return True

        print(f"\n[{self.name}] Waiting for {len(slurm_tasks)} Slurm tasks...")

        for task in slurm_tasks:
            if task.get_status() == "completed":
                continue

            success = task.wait_for_completion(poll_interval)
            if not success:
                return False

        return True


class Pipeline:
    """Manages multiple algorithms."""

    def __init__(self, target_name: str, input_fasta: pathlib.Path,
                 output_root: pathlib.Path, slurm_enabled: bool = True):
        self.target_name = target_name
        self.input_fasta = input_fasta
        self.output_root = output_root
        self.slurm_enabled = slurm_enabled
        self.algorithms: list[Algorithm] = []

        # Create output directory
        self.output_root.mkdir(parents=True, exist_ok=True)

    def add_algorithm(self, algorithm: Algorithm):
        """Add an algorithm to the pipeline."""
        self.algorithms.append(algorithm)

    def run(self, resume: bool = True, wait: bool = False) -> bool:
        """Run all algorithms.

        Args:
            resume: Skip completed tasks
            wait: Wait for Slurm jobs to complete

        Returns:
            True if all succeeded
        """
        for algo in self.algorithms:
            success = algo.run(resume=resume)
            if not success:
                print(f"\nAlgorithm {algo.name} failed")
                return False

            if wait:
                success = algo.wait_all()
                if not success:
                    print(f"\nAlgorithm {algo.name} jobs failed")
                    return False

        print(f"\n{'='*60}")
        print("Pipeline completed successfully")
        print(f"{'='*60}")
        return True
