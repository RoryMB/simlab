"""ZMQ ROUTER server for multiplexing parallel environment communications."""

import json
import threading

import zmq


class ZMQRouterServer:
    """Centralized ROUTER server that dispatches messages to environment-specific robot handlers.

    Replaces the per-robot REQ/REP pattern with a single ROUTER socket that routes
    messages based on client identity (env_id.robot_type format).
    """

    def __init__(self, simulation_app, port: int = 5555):
        """Initialize ROUTER server.

        Args:
            simulation_app: Isaac Sim application instance
            port: Port to bind ROUTER socket (default: 5555)
        """
        self.simulation_app = simulation_app
        self.port = port
        self.context = None
        self.socket = None
        self.handlers: dict[str, any] = {}  # identity -> ZMQ_Robot_Server instance
        self._thread = None

    def register_handler(self, env_id: int, robot_type: str, handler):
        """Register a robot handler for a specific environment.

        Args:
            env_id: Environment ID (0-N)
            robot_type: Robot type (e.g., "pf400", "peeler", "thermocycler")
            handler: ZMQ_Robot_Server instance that handles commands
        """
        identity = f"env_{env_id}.{robot_type}"
        self.handlers[identity] = handler
        print(f"Registered handler: {identity}")

    def start_server(self):
        """Start ROUTER server in background thread."""
        self._thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        self._thread.start()
        return self._thread

    def zmq_server_thread(self):
        """ROUTER server running in background thread."""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(f"tcp://*:{self.port}")

        print(f"ZMQ ROUTER server listening on port {self.port}")

        while self.simulation_app.is_running():
            try:
                if self.socket.poll(100):
                    # ROUTER receives: [identity, empty, message]
                    identity_bytes, empty, message_bytes = self.socket.recv_multipart(zmq.NOBLOCK)
                    identity = identity_bytes.decode()
                    request = json.loads(message_bytes.decode())

                    print(f"ROUTER received command for {identity}: {request}")

                    # Find handler for this identity
                    handler = self.handlers.get(identity)
                    if handler:
                        response = handler.handle_command(request)
                        print(f"ROUTER sending response to {identity}: {response}")
                        self.socket.send_multipart([
                            identity_bytes,
                            empty,
                            json.dumps(response).encode(),
                        ])
                    else:
                        error_response = {
                            "status": "error",
                            "message": f"No handler registered for identity: {identity}",
                        }
                        print(f"ROUTER error: {error_response['message']}")
                        self.socket.send_multipart([
                            identity_bytes,
                            empty,
                            json.dumps(error_response).encode(),
                        ])

            except zmq.Again:
                continue
            except Exception as e:
                print(f"ROUTER server error: {e}")
                import traceback
                traceback.print_exc()

        self.cleanup()

    def cleanup(self):
        """Clean up ZMQ resources."""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
