"""REST Gateway that routes requests to multiple robot nodes via path-based routing.

This gateway consolidates multiple robot REST nodes into a single process, replacing
the need for individual ports per robot. Requests are routed based on URL path:

    POST /env_0/pf400/actions/transfer -> SimPF400Node.transfer()
    GET /env_0/pf400/state -> SimPF400Node.state_handler() + get_state()

Usage:
    python -m slcore.gateway.rest_gateway --num-envs 5 --port 8000
"""

from __future__ import annotations

import argparse
import signal
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request


def _get_node_registry() -> dict[str, tuple[type, type]]:
    """Lazy import of node classes to avoid MADSci argument parser interference."""
    from slcore.robots.hidex.sim_hidex_rest_node import SimHidexNode, SimHidexNodeConfig
    from slcore.robots.ot2.sim_ot2_rest_node import SimOT2Node, SimOT2NodeConfig
    from slcore.robots.peeler.sim_peeler_rest_node import SimPeelerNode, SimPeelerNodeConfig
    from slcore.robots.pf400.sim_pf400_rest_node import SimPF400Node, SimPF400NodeConfig
    from slcore.robots.sealer.sim_sealer_rest_node import SimSealerNode, SimSealerNodeConfig
    from slcore.robots.thermocycler.sim_thermocycler_rest_node import (
        SimThermocyclerNode,
        SimThermocyclerNodeConfig,
    )
    from slcore.robots.ur5e.sim_ur5e_rest_node import SimUR5eNode, SimUR5eNodeConfig
    return {
        "hidex": (SimHidexNode, SimHidexNodeConfig),
        "ot2": (SimOT2Node, SimOT2NodeConfig),
        "peeler": (SimPeelerNode, SimPeelerNodeConfig),
        "pf400": (SimPF400Node, SimPF400NodeConfig),
        "sealer": (SimSealerNode, SimSealerNodeConfig),
        "thermocycler": (SimThermocyclerNode, SimThermocyclerNodeConfig),
        "ur5e": (SimUR5eNode, SimUR5eNodeConfig),
    }

# Node registry is loaded lazily via _get_node_registry() to avoid
# MADSci argument parser interference at import time


class NodeManager:
    """Manages node instances keyed by (env_id, robot_type)."""

    def __init__(self):
        self._nodes: dict[tuple[str, str], Any] = {}

    def register(self, env_id: str, robot_type: str, node: Any) -> None:
        """Register a node instance."""
        key = (env_id, robot_type)
        self._nodes[key] = node

    def get(self, env_id: str, robot_type: str) -> Any:
        """Get a node instance, raising HTTPException if not found."""
        key = (env_id, robot_type)
        if key not in self._nodes:
            raise HTTPException(
                status_code=404,
                detail=f"Node not found: {env_id}/{robot_type}",
            )
        return self._nodes[key]

    def get_all(self) -> list[tuple[str, str, Any]]:
        """Get all registered nodes as (env_id, robot_type, node) tuples."""
        return [(k[0], k[1], v) for k, v in self._nodes.items()]

    def shutdown_all(self) -> None:
        """Call shutdown_handler on all nodes."""
        for (env_id, robot_type), node in self._nodes.items():
            try:
                print(f"Shutting down {env_id}/{robot_type}...")
                node.shutdown_handler()
            except Exception as e:
                print(f"Error shutting down {env_id}/{robot_type}: {e}")


class RestGateway:
    """REST Gateway that consolidates multiple robot nodes into a single process."""

    def __init__(
        self,
        num_envs: int = 5,
        robot_types: list[str] = None,
        zmq_server_url: str = "tcp://localhost:5555",
        resource_server_url: str = "http://localhost:8013",
        port: int = 8000,
    ):
        self.num_envs = num_envs
        self.robot_types = robot_types or ["pf400", "peeler", "thermocycler"]
        self.zmq_server_url = zmq_server_url
        self.resource_server_url = resource_server_url
        self.port = port
        self.node_manager = NodeManager()
        self.app: FastAPI = None

    def _create_node(self, robot_type: str, env_id: int) -> Any:
        """Create a node instance with appropriate config."""
        node_registry = _get_node_registry()
        if robot_type not in node_registry:
            raise ValueError(f"Unknown robot type: {robot_type}")

        node_cls, config_cls = node_registry[robot_type]

        # Build config - PF400 has resource_server_url, simple devices don't
        config_kwargs = {
            "zmq_server_url": self.zmq_server_url,
            "env_id": env_id,
        }

        # Only add resource_server_url if the config class supports it
        if hasattr(config_cls, "model_fields") and "resource_server_url" in config_cls.model_fields:
            config_kwargs["resource_server_url"] = self.resource_server_url

        config = config_cls(**config_kwargs)
        node = node_cls(node_config=config)
        return node

    def initialize_all_nodes(self) -> None:
        """Initialize all nodes eagerly at startup."""
        print(f"Initializing {self.num_envs} environments with robots: {self.robot_types}")

        for env_id in range(self.num_envs):
            env_key = f"env_{env_id}"
            for robot_type in self.robot_types:
                print(f"  Initializing {env_key}/{robot_type}...")
                node = self._create_node(robot_type, env_id)

                try:
                    node.startup_handler()
                    # Mark node as no longer initializing (normally done by _startup())
                    # This enables node_status.ready to return True
                    node.node_status.initializing = False
                    self.node_manager.register(env_key, robot_type, node)
                    print(f"    {env_key}/{robot_type} ready")
                except Exception as e:
                    print(f"    ERROR initializing {env_key}/{robot_type}: {e}")
                    raise

        print(f"Gateway ready on port {self.port}")

    def create_app(self) -> FastAPI:
        """Create the FastAPI application with all routes."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            self.initialize_all_nodes()
            yield
            # Shutdown
            self.node_manager.shutdown_all()

        app = FastAPI(
            title="Simlab REST Gateway",
            description="Consolidated REST API for multiple simulation robot nodes",
            version="1.0.0",
            lifespan=lifespan,
        )

        self._configure_routes(app)
        self.app = app
        return app

    def _configure_routes(self, app: FastAPI) -> None:
        """Configure all API routes."""

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "nodes": len(self.node_manager._nodes)}

        @app.get("/nodes")
        async def list_nodes():
            """List all registered nodes."""
            nodes = []
            for env_id, robot_type, node in self.node_manager.get_all():
                nodes.append({
                    "env_id": env_id,
                    "robot_type": robot_type,
                    "actions": list(node.action_handlers.keys()),
                })
            return {"nodes": nodes}

        @app.get("/{env_id}/{robot_type}/info")
        async def get_info(env_id: str, robot_type: str):
            """Get node info (MADSci endpoint)."""
            node = self.node_manager.get(env_id, robot_type)
            return node.get_info()

        @app.get("/{env_id}/{robot_type}/status")
        async def get_status(env_id: str, robot_type: str):
            """Get node status (MADSci endpoint)."""
            node = self.node_manager.get(env_id, robot_type)
            return node.get_status()

        @app.get("/{env_id}/{robot_type}/state")
        async def get_state(env_id: str, robot_type: str):
            """Get node state (MADSci endpoint)."""
            node = self.node_manager.get(env_id, robot_type)
            node.state_handler()  # Update state from interface
            return node.get_state()

        @app.get("/{env_id}/{robot_type}/action")
        async def get_action_history(env_id: str, robot_type: str):
            """Get action history (MADSci endpoint)."""
            node = self.node_manager.get(env_id, robot_type)
            return node.get_action_history()

        @app.get("/{env_id}/{robot_type}/action/{action_id}/status")
        async def get_action_status(env_id: str, robot_type: str, action_id: str):
            """Get status of a specific action (MADSci endpoint)."""
            node = self.node_manager.get(env_id, robot_type)
            return node.get_action_status(action_id)

        @app.get("/{env_id}/{robot_type}/action/{action_id}/result")
        async def get_action_result(env_id: str, robot_type: str, action_id: str):
            """Get result of a specific action (MADSci endpoint)."""
            node = self.node_manager.get(env_id, robot_type)
            return node.get_action_result(action_id)

        # Store pending actions for the two-step create/start pattern
        pending_actions: dict[str, tuple[Any, str, dict]] = {}  # action_id -> (node, action_name, args)

        @app.post("/{env_id}/{robot_type}/action/{action_name}")
        async def create_action(
            env_id: str,
            robot_type: str,
            action_name: str,
            request: Request,
        ):
            """Create an action (MADSci endpoint). Returns action_id for use with /start."""
            node = self.node_manager.get(env_id, robot_type)

            # Verify action exists
            if action_name not in node.action_handlers:
                raise HTTPException(
                    status_code=404,
                    detail=f"Action '{action_name}' not found on {env_id}/{robot_type}. "
                           f"Available actions: {list(node.action_handlers.keys())}",
                )

            # Parse request body
            try:
                body = await request.json()
            except Exception:
                body = {}

            # Extract args - handle both flat and nested {"args": {...}} formats
            args = body.get("args", body)
            if isinstance(args, dict) and "args" in args:
                args = args["args"]

            # Generate action_id and store for later execution
            from madsci.common.utils import new_ulid_str
            action_id = new_ulid_str()

            # Store the pending action with extracted args
            pending_actions[action_id] = (node, action_name, args)

            return {"action_id": action_id}

        @app.post("/{env_id}/{robot_type}/action/{action_name}/{action_id}/start")
        async def start_action(
            env_id: str,
            robot_type: str,
            action_name: str,
            action_id: str,
        ):
            """Start a previously created action (MADSci endpoint)."""
            if action_id not in pending_actions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Action '{action_id}' not found. Create it first with POST /action/{action_name}",
                )

            node, stored_action_name, args = pending_actions.pop(action_id)

            # Verify action_name matches
            if stored_action_name != action_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Action name mismatch: expected '{stored_action_name}', got '{action_name}'",
                )

            # Create and run action request
            from madsci.common.types.action_types import ActionRequest

            action_request = ActionRequest(
                action_id=action_id,
                action_name=action_name,
                args=args,
            )

            result = node.run_action(action_request)
            return self._action_result_to_dict(result)

        @app.post("/{env_id}/{robot_type}/admin/{admin_command}")
        async def run_admin_command(env_id: str, robot_type: str, admin_command: str):
            """Run an admin command on a node (MADSci endpoint)."""
            node = self.node_manager.get(env_id, robot_type)
            from madsci.common.types.node_types import AdminCommands

            try:
                cmd = AdminCommands(admin_command)
                return node.run_admin_command(cmd)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown admin command: {admin_command}",
                )

    def _action_result_to_dict(self, result) -> dict:
        """Convert ActionResult to JSON-serializable dictionary."""
        return {
            "action_id": result.action_id,
            "status": result.status.value if hasattr(result.status, "value") else str(result.status),
            "errors": [
                error.model_dump() if hasattr(error, "model_dump") else str(error)
                for error in (result.errors or [])
            ],
            "json_result": result.json_result,
            "files": None,
            "datapoints": result.datapoints.model_dump() if result.datapoints else None,
        }

    def run(self) -> None:
        """Run the gateway server."""
        uvicorn.run(
            self.create_app(),
            host="0.0.0.0",
            port=self.port,
        )


def run_gateway():
    """CLI entry point for running the gateway."""
    parser = argparse.ArgumentParser(description="REST Gateway for robot nodes")
    parser.add_argument(
        "--num-envs",
        type=int,
        default=5,
        help="Number of environments (default: 5)",
    )
    parser.add_argument(
        "--robot-types",
        type=str,
        default="pf400,peeler,thermocycler",
        help="Comma-separated list of robot types (default: pf400,peeler,thermocycler)",
    )
    parser.add_argument(
        "--zmq-server-url",
        type=str,
        default="tcp://localhost:5555",
        help="ZMQ server URL (default: tcp://localhost:5555)",
    )
    parser.add_argument(
        "--resource-server-url",
        type=str,
        default="http://localhost:8013",
        help="Resource server URL (default: http://localhost:8013)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Gateway port (default: 8000)",
    )

    args = parser.parse_args()

    gateway = RestGateway(
        num_envs=args.num_envs,
        robot_types=args.robot_types.split(","),
        zmq_server_url=args.zmq_server_url,
        resource_server_url=args.resource_server_url,
        port=args.port,
    )

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\nReceived shutdown signal...")
        gateway.node_manager.shutdown_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    gateway.run()


if __name__ == "__main__":
    run_gateway()
