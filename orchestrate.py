"""
Autolab System Orchestrator

Coordinates the startup and shutdown of the 4-terminal Autolab system:
1. Robot Nodes
2. Isaac Sim
3. MADSci
4. Workflow submission

Usage:
python orchestrate.py \
    --node-cmd ". activate-madsci.sh && cd src/madsci/ && ./run_node_ur5e.sh" \
    --node-cmd ". activate-madsci.sh && cd src/madsci/ && ./run_node_ot2.sh" \
    --isaac-cmd ". activate-isaacsim.sh && cd src/isaacsim/ && python run.py" \
    --madsci-cmd "cd src/madsci/ && ./run_madsci.sh" \
    --workflow-cmd ". activate-madsci.sh && cd projects/prototyping/ && python run_workflow.py workflow.yaml" \
    --nodes-ready-keyword "EventType.NODE_START" \
    --isaac-ready-keyword "Simulation App Startup Complete" \
    --madsci-ready-keyword "Uvicorn running on http://localhost:8015" \
    --timeout 30
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from asyncio.subprocess import PIPE
from typing import Optional


logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

class ProcessManager:
    def __init__(self):
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.shutdown_event = asyncio.Event()
        self.ready_flags: set[str] = set()

    async def start_process(self, name: str, command: str) -> Optional[asyncio.subprocess.Process]:
        """Start a subprocess with shell execution"""
        logger.info(f"Starting {name}: {command}")

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=PIPE,
            stderr=PIPE,
            preexec_fn=os.setsid,  # Create new process group for clean shutdown
        )

        self.processes[name] = process
        return process

    async def monitor_output(
        self,
        name: str,
        process: asyncio.subprocess.Process,
        ready_keyword: str,
        stream_name: str = "stdout",
    ):
        """Monitor process output for ready keyword and general logging"""
        stream = process.stdout if stream_name == "stdout" else process.stderr

        while True:
            line = await stream.readline()
            if not line:
                break

            line_str = line.decode().strip()
            if name in self.ready_flags:
                logger.info(f"[{name.upper()}] {line_str}")

            # Check for ready keyword
            if ready_keyword and ready_keyword in line_str and name not in self.ready_flags:
                logger.info(f"{name} is ready!")
                self.ready_flags.add(name)

    async def wait_for_ready(self, name: str, timeout: int = 120):
        """Wait for a service to be ready with timeout"""
        start_time = asyncio.get_event_loop().time()

        while name not in self.ready_flags and not self.shutdown_event.is_set():
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"{name} failed to start within {timeout} seconds")
            await asyncio.sleep(0.1)

    async def shutdown_process(self, name: str):
        """Gracefully shutdown a process"""
        if name not in self.processes:
            return

        process = self.processes[name]
        if process.returncode is not None:
            logger.info(f"{name} already terminated")
            return

        logger.info(f"Shutting down {name}...")

        # Send SIGINT (Ctrl-C) to process group
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGINT)

            # Wait for graceful shutdown
            await asyncio.wait_for(process.wait(), timeout=10)
            logger.info(f"{name} shutdown gracefully")

        except asyncio.TimeoutError:
            logger.warning(f"{name} did not shutdown gracefully, forcing termination")
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                await process.wait()
            except ProcessLookupError:
                pass  # Process already dead

    async def shutdown_all(self):
        """Shutdown all processes in reverse order"""
        self.shutdown_event.set()

        # Shutdown workflow first
        await self.shutdown_process('workflow')

        # Shutdown all node processes
        node_names = [name for name in self.processes.keys() if name.startswith('node_')]
        for name in node_names:
            await self.shutdown_process(name)

        # Shutdown MADSci and Isaac
        await self.shutdown_process('madsci')
        await self.shutdown_process('isaac')

    def check_process_health(self):
        """Check if any critical processes have died"""
        for name, process in self.processes.items():
            if process.returncode is not None and process.returncode != 0:
                logger.error(f"{name} process failed with return code {process.returncode}")
                return False
        return True

def setup_signal_handlers(pm: ProcessManager):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, initiating graceful shutdown...")
        asyncio.create_task(pm.shutdown_all())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    parser = argparse.ArgumentParser(description="Orchestrate Autolab system startup and coordination")

    parser.add_argument('--isaac-cmd', required=True, help='Command to start Isaac Sim')
    parser.add_argument('--madsci-cmd', required=True, help='Command to start MADSci services')
    parser.add_argument('--node-cmd', action='append', required=True, help='Command to start a robot node (can be used multiple times)')
    parser.add_argument('--workflow-cmd', required=True, help='Command to submit workflow')

    parser.add_argument('--isaac-ready-keyword', default='Ready', help='Keyword to detect Isaac Sim readiness')
    parser.add_argument('--madsci-ready-keyword', default='Started', help='Keyword to detect MADSci readiness')
    parser.add_argument('--nodes-ready-keyword', default='Connected', help='Keyword to detect robot nodes readiness')

    parser.add_argument('--timeout', type=int, default=60, help='How long to wait for each process to initialize')

    args = parser.parse_args()

    pm = ProcessManager()
    setup_signal_handlers(pm)

    for i, node_cmd in enumerate(args.node_cmd):
        node_process = await pm.start_process(f'node_{i}', node_cmd)
        asyncio.create_task(pm.monitor_output(f'node_{i}', node_process, args.nodes_ready_keyword))

    isaac_process = await pm.start_process('isaac', args.isaac_cmd)
    asyncio.create_task(pm.monitor_output('isaac', isaac_process, args.isaac_ready_keyword))

    madsci_process = await pm.start_process('madsci', args.madsci_cmd)
    asyncio.create_task(pm.monitor_output('madsci', madsci_process, args.madsci_ready_keyword))

    # Wait for all nodes, Isaac, and MADSci to be ready
    for i in range(len(args.node_cmd)):
        await pm.wait_for_ready(f'node_{i}', args.timeout)
    await pm.wait_for_ready('isaac', args.timeout)
    await pm.wait_for_ready('madsci', args.timeout)

    if pm.shutdown_event.is_set():
        logger.error("System failed")
        return 1

    logger.info("=== Submitting Workflow ===")

    workflow_process = await pm.start_process('workflow', args.workflow_cmd)
    asyncio.create_task(pm.monitor_output('workflow', workflow_process, None))

    # Monitor system health and wait for shutdown signal
    while not pm.shutdown_event.is_set():
        if not pm.check_process_health():
            logger.error("Process health check failed, initiating shutdown")
            await pm.shutdown_all()
            logger.error("System failed")
            return 1

        await asyncio.sleep(1)

    logger.info("System shutdown completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
