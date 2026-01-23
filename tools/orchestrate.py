"""
Simlab System Orchestrator

Coordinates the startup and shutdown of the Simlab system. Supports running
the full system (Isaac Sim + Gateway + MADSci + Workflow) or a minimal setup
(Isaac Sim + Workflow) for direct testing.

All process output is logged to /tmp/simlab/<timestamp>/ with separate files
for startup and runtime phases. Console shows only status messages and errors.

Usage (full system):
python orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/my-project && python run.py" \
    --gateway-cmd "source activate-madsci.sh && python -m slcore.gateway.rest_gateway --num-envs 5" \
    --madsci-cmd "cd projects/my-project/madsci/ && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/my-project && python run_workflow.py workflow.yaml"

Usage (minimal - Isaac Sim + workflow only):
python orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/my-project && python run.py" \
    --workflow-cmd "source activate-madsci.sh && python my_test_script.py"
"""

import argparse
import asyncio
import logging
import os
import re
import signal
import sys
from asyncio.subprocess import PIPE
from datetime import datetime
from typing import IO, Optional


logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Case-insensitive error detection pattern
ERROR_PATTERN = re.compile(r'\b(error|exception|traceback|failed)\b', re.IGNORECASE)


class LogManager:
    """Manages log files for all processes, splitting by startup/runtime phase."""

    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.log_files: dict[str, IO] = {}
        self.current_phase: dict[str, str] = {}  # 'startup' or 'runtime'
        self.detected_errors: list[tuple[str, str]] = []  # (process_name, error_line)

    def _get_log_file(self, process_name: str) -> IO:
        """Get or create log file handle for current phase."""
        if process_name == 'workflow':
            filename = 'workflow.log'
        else:
            phase = self.current_phase.get(process_name, 'startup')
            filename = f'{process_name}_{phase}.log'

        filepath = os.path.join(self.run_dir, filename)

        if filepath not in self.log_files:
            self.log_files[filepath] = open(filepath, 'a')

        return self.log_files[filepath]

    def write_line(self, process_name: str, line: str):
        """Write line to appropriate log file."""
        if process_name not in self.current_phase and process_name != 'workflow':
            self.current_phase[process_name] = 'startup'

        log_file = self._get_log_file(process_name)
        log_file.write(line + '\n')
        log_file.flush()

    def switch_to_runtime(self, process_name: str):
        """Switch from startup to runtime phase."""
        if process_name == 'workflow':
            return

        old_phase = self.current_phase.get(process_name, 'startup')
        old_filename = f'{process_name}_{old_phase}.log'
        old_filepath = os.path.join(self.run_dir, old_filename)

        if old_filepath in self.log_files:
            self.log_files[old_filepath].close()
            del self.log_files[old_filepath]

        self.current_phase[process_name] = 'runtime'

    def check_for_error(self, process_name: str, line: str) -> bool:
        """Check for error keywords and store if found."""
        if ERROR_PATTERN.search(line):
            self.detected_errors.append((process_name, line))
            return True
        return False

    def close_all(self):
        """Close all open log file handles."""
        for f in self.log_files.values():
            try:
                f.close()
            except Exception:
                pass
        self.log_files.clear()


class ProcessManager:
    def __init__(self, log_manager: LogManager):
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.shutdown_event = asyncio.Event()
        self.ready_flags: set[str] = set()
        self.log_manager = log_manager
        self.exit_codes: dict[str, int] = {}

    async def start_process(self, name: str, command: str) -> Optional[asyncio.subprocess.Process]:
        """Start a subprocess with shell execution."""
        logger.info(f"Starting {name}: {command}")

        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=PIPE,
            stderr=PIPE,
            preexec_fn=os.setsid,
            executable='/bin/bash',
            env=env,
        )

        self.processes[name] = process
        return process

    async def monitor_output(
        self,
        name: str,
        process: asyncio.subprocess.Process,
        ready_keyword: Optional[str],
    ):
        """Monitor process output, log to files, and detect errors."""
        while True:
            line = await process.stdout.readline()
            if not line:
                break

            line_str = line.decode().strip()

            # Write all output to log file
            self.log_manager.write_line(name, line_str)

            # Check for errors and print to console if found
            if self.log_manager.check_for_error(name, line_str):
                logger.info(f"[{name.upper()}] {line_str}")

            # Check for ready keyword
            if ready_keyword and ready_keyword in line_str and name not in self.ready_flags:
                logger.info(f"{name} is ready!")
                self.ready_flags.add(name)
                self.log_manager.switch_to_runtime(name)

    async def wait_for_ready(self, name: str, timeout: int = 120):
        """Wait for a service to be ready with timeout."""
        start_time = asyncio.get_event_loop().time()

        while name not in self.ready_flags and not self.shutdown_event.is_set():
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"{name} failed to start within {timeout} seconds")
            if rc_name := self.check_process_health():
                raise TimeoutError(f"{rc_name} exited while {name} was starting")
            await asyncio.sleep(0.1)

    async def shutdown_process(self, name: str):
        """Gracefully shutdown a process."""
        if name not in self.processes:
            return

        process = self.processes[name]
        if process.returncode is not None:
            logger.info(f"{name} already terminated")
            return

        logger.info(f"Shutting down {name}...")

        try:
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
            await asyncio.wait_for(process.wait(), timeout=10)
            logger.info(f"{name} shutdown gracefully")

        except asyncio.TimeoutError:
            logger.warning(f"{name} did not shutdown gracefully, forcing termination")
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                await process.wait()
            except ProcessLookupError:
                pass

    async def shutdown_all(self):
        """Shutdown all processes in reverse order."""
        self.shutdown_event.set()

        await self.shutdown_process('workflow')
        await self.shutdown_process('gateway')
        await self.shutdown_process('madsci')
        await self.shutdown_process('isaac')

    def check_process_health(self) -> Optional[str]:
        """Check if any processes have exited and track exit codes."""
        for name, process in self.processes.items():
            if process.returncode is not None and name not in self.exit_codes:
                self.exit_codes[name] = process.returncode
                if process.returncode != 0:
                    logger.info(f"{name} exited with code {process.returncode}")
                return name
        return None


def format_size(bytes_count: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024:
            if unit == 'B':
                return f"{bytes_count} {unit}"
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def generate_summary(pm: ProcessManager, log_manager: LogManager):
    """Generate end-of-run summary."""
    log_manager.close_all()

    # Determine outcome based on exit codes only
    # (error pattern matching is for display, not success determination)
    failed_processes = {name: code for name, code in pm.exit_codes.items() if code != 0}
    success = len(failed_processes) == 0

    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)

    # 1. Outcome
    if success:
        print("Outcome: SUCCESS")
    else:
        print("Outcome: FAILURE")
        for name, code in failed_processes.items():
            print(f"  - {name} exited with code {code}")

    # 2. Last 20 lines of workflow.log
    workflow_log = os.path.join(log_manager.run_dir, 'workflow.log')
    if os.path.exists(workflow_log):
        print("\nWorkflow Log (last 20 lines):")
        print("-" * 40)
        with open(workflow_log, 'r') as f:
            lines = f.readlines()
            for line in lines[-20:]:
                print(line.rstrip())
        print("-" * 40)

    # 3. Log file paths with sizes
    print("\nLog Files:")
    if os.path.exists(log_manager.run_dir):
        for filename in sorted(os.listdir(log_manager.run_dir)):
            filepath = os.path.join(log_manager.run_dir, filename)
            size = os.path.getsize(filepath)
            print(f"  {filepath} ({format_size(size)})")

    print("=" * 60)


def setup_signal_handlers(pm: ProcessManager):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, initiating graceful shutdown...")
        asyncio.create_task(pm.shutdown_all())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    parser = argparse.ArgumentParser(description="Orchestrate Simlab system startup and coordination")

    parser.add_argument('--isaac-cmd', required=True, help='Command to start Isaac Sim')
    parser.add_argument('--gateway-cmd', default=None, help='Command to start REST gateway (optional)')
    parser.add_argument('--madsci-cmd', default=None, help='Command to start MADSci services (optional)')
    parser.add_argument('--workflow-cmd', required=True, help='Command to submit workflow')

    parser.add_argument('--isaac-ready-keyword', default='Simulation App Startup Complete', help='Keyword to detect Isaac Sim readiness')
    parser.add_argument('--gateway-ready-keyword', default='Gateway ready', help='Keyword to detect gateway readiness')
    parser.add_argument('--madsci-ready-keyword', default='Uvicorn running on http://localhost:8015', help='Keyword to detect MADSci readiness')

    parser.add_argument('--timeout', type=int, default=60, help='How long to wait for each process to initialize')

    args = parser.parse_args()

    # Create run directory for logs
    run_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    run_dir = f'/tmp/simlab/{run_timestamp}'
    os.makedirs(run_dir, exist_ok=True)
    logger.info(f"Logs: {run_dir}/")

    log_manager = LogManager(run_dir)
    pm = ProcessManager(log_manager)
    setup_signal_handlers(pm)

    isaac_cmd_with_redirect = f"({args.isaac_cmd}) 2>&1"
    isaac_process = await pm.start_process('isaac', isaac_cmd_with_redirect)
    asyncio.create_task(pm.monitor_output('isaac', isaac_process, args.isaac_ready_keyword))

    # Let Isaac have an extra moment to stabilize
    await asyncio.sleep(20)

    # Start gateway if provided
    if args.gateway_cmd:
        gateway_cmd_with_redirect = f"({args.gateway_cmd}) 2>&1"
        gateway_process = await pm.start_process('gateway', gateway_cmd_with_redirect)
        asyncio.create_task(pm.monitor_output('gateway', gateway_process, args.gateway_ready_keyword))

    # Start MADSci if provided
    if args.madsci_cmd:
        madsci_cmd_with_redirect = f"({args.madsci_cmd}) 2>&1"
        madsci_process = await pm.start_process('madsci', madsci_cmd_with_redirect)
        asyncio.create_task(pm.monitor_output('madsci', madsci_process, args.madsci_ready_keyword))

    # Wait for Isaac, gateway, and MADSci to be ready
    try:
        await pm.wait_for_ready('isaac', args.timeout)
        if args.gateway_cmd:
            await pm.wait_for_ready('gateway', args.timeout)
        if args.madsci_cmd:
            await pm.wait_for_ready('madsci', args.timeout)
    except Exception as e:
        logger.info(f"Error while starting processes: {e}")
        await pm.shutdown_all()

    if pm.shutdown_event.is_set() or pm.check_process_health():
        logger.error("System failed")
        await pm.shutdown_all()
        generate_summary(pm, log_manager)
        return 1

    logger.info("=== Submitting Workflow ===")

    workflow_cmd_with_redirect = f"({args.workflow_cmd}) 2>&1"
    workflow_process = await pm.start_process('workflow', workflow_cmd_with_redirect)
    log_manager.current_phase['workflow'] = 'runtime'  # Workflow has no startup phase
    pm.ready_flags.add('workflow')
    asyncio.create_task(pm.monitor_output('workflow', workflow_process, None))

    # Monitor system health and wait for shutdown signal
    while not pm.shutdown_event.is_set():
        if pm.check_process_health():
            logger.info("Health check indicated a process is no longer running, initiating shutdown")
            await pm.shutdown_all()

        await asyncio.sleep(1)

    generate_summary(pm, log_manager)
    logger.info("System shutdown completed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
