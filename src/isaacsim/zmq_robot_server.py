import json
import threading
import zmq
from abc import ABC, abstractmethod

class ZMQ_Robot_Server(ABC):
    """Base class for ZMQ robot servers handling communication between Isaac Sim and MADSci"""
    
    def __init__(self, simulation_app, robot, robot_name: str, port: int, motion_type: str = "teleport"):
        self.simulation_app = simulation_app
        self.robot = robot  # Isaac Sim Robot object from world.scene.add(Robot(...))
        self.robot_name = robot_name
        self.port = port
        self.motion_type = motion_type  # "teleport" or "smooth"
        self.context = None
        self.socket = None

    def start_server(self):
        """Start ZMQ server in background thread"""
        zmq_thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        zmq_thread.start()
        return zmq_thread

    def zmq_server_thread(self):
        """ZMQ server running in background thread"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        print(f"{self.robot_name} ZMQ server listening on port {self.port}")

        while self.simulation_app.is_running():
            try:
                # Receive request with timeout
                if self.socket.poll(100):  # 100ms timeout
                    message = self.socket.recv_string(zmq.NOBLOCK)
                    request = json.loads(message)

                    print(f"{self.robot_name} received command: {request}")

                    # Handle command using robot-specific handler
                    response = self.handle_command(request)

                    print(f"{self.robot_name} sending response: {response}")

                    # Send response
                    self.socket.send_string(json.dumps(response))

            except zmq.Again:
                continue
            except Exception as e:
                print(f"ZMQ server error for {self.robot_name}: {e}")
                error_response = {"status": "error", "message": str(e)}
                try:
                    self.socket.send_string(json.dumps(error_response))
                except:
                    pass  # Socket might be closed

        self.cleanup()

    def cleanup(self):
        """Clean up ZMQ resources"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()

    @abstractmethod
    def handle_command(self, request):
        """Handle incoming ZMQ command from MADSci - must be implemented by subclasses"""
        pass

    def create_success_response(self, message: str = "success", **kwargs):
        """Helper to create standardized success response"""
        response = {"status": "success", "message": message}
        response.update(kwargs)
        return response

    def create_error_response(self, message: str):
        """Helper to create standardized error response"""
        return {"status": "error", "message": message}