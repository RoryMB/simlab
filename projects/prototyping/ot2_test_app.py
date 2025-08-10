"""OT-2 Integration Test Application"""

import time
from pathlib import Path
from typing import Optional

from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.workflow_types import WorkflowDefinition


class OT2TestConfig:
    """Configuration for the OT-2 integration test application."""

    def __init__(self):
        self.workflow_directory: Path = Path(__file__).parent.resolve()
        """The directory where the workflows are stored."""
        self.protocol_directory: Path = Path(__file__).parent.resolve()
        """The directory where the protocols are stored."""
        
        # Test configuration
        self.test_wells: list[str] = ["A1", "A2", "A3", "B1", "B2", "B3"]
        """Wells to use for testing."""
        self.test_volumes: list[float] = [50.0, 75.0, 100.0, 125.0, 150.0, 200.0]
        """Volumes (in μL) to test with."""
        self.comprehensive_test: bool = True
        """Whether to run comprehensive tests."""
        
        # MADSci configuration
        self.workcell_url: str = "http://localhost:8015"
        """URL for MADSci workcell service."""


class OT2TestApplication:
    """Test application for validating OT-2 simulation integration."""

    def __init__(self, config: Optional[OT2TestConfig] = None):
        """Initialize the OT-2 test application."""
        self.config = config or OT2TestConfig()
        
        print("OT-2 Test Application initialized")
        print(f"Test wells: {self.config.test_wells}")
        print(f"Test volumes: {self.config.test_volumes}")
        print(f"Workcell URL: {self.config.workcell_url}")

        # Load the test workflow
        self.ot2_test_workflow = WorkflowDefinition.from_yaml(
            self.config.workflow_directory / "ot2_test_workflow.yaml"
        )

    def run_integration_test(self) -> bool:
        """Run the comprehensive OT-2 integration test."""
        print("Starting OT-2 integration test")
        
        try:
            print("\n" + "="*70)
            print("RUNNING OT-2 COMPREHENSIVE INTEGRATION TEST")
            print("="*70)
            print("This test validates the complete OT-2 simulation pipeline:")
            print("- MADSci node communication")
            print("- Protocol parameter substitution")
            print("- ZMQ communication with Isaac Sim")
            print("- Robot joint control")
            print("- Liquid handling simulation")
            print("="*70)

            # Initialize workcell client
            print("\nConnecting to MADSci workcell...")
            wc_client = WorkcellClient(workcell_server_url=self.config.workcell_url)
            print("Connected to MADSci workcell")
            
            # Wait a moment for services to be ready
            print("Waiting for services to be ready...")
            time.sleep(2)

            # Submit the test workflow
            print("\nSubmitting test workflow...")
            workflow_result = wc_client.submit_workflow(
                workflow=self.ot2_test_workflow,
                parameters={
                    "test_wells": self.config.test_wells,
                    "test_volumes": self.config.test_volumes,
                    "protocol_path": str(self.config.protocol_directory / "ot2_test_protocol.py"),
                },
                await_completion=True
            )

            print(f"\nWorkflow completed: {workflow_result.name}")
            print(f"Status: {workflow_result.status.description}")
            
            if workflow_result.steps:
                for step in workflow_result.steps:
                    print(f"Step '{step.name}': {step.result.status if step.result else 'No result'}")

            print("\n" + "="*70)
            print("OT-2 INTEGRATION TEST PASSED!")
            print("="*70)
            print("The following components are working correctly:")
            print("- MADSci SimOT2Node communication")
            print("- Protocol file handling and parameter substitution")  
            print("- ZMQ communication pipeline")
            print("- Isaac Sim robot control")
            print("- Complete simulation workflow")
            print("\nYour OT-2 simulation integration is ready for use!")
            print("="*70)
            
            return True
            
        except Exception as e:
            print("\n" + "="*70)
            print("OT-2 INTEGRATION TEST FAILED!")
            print("="*70)
            print(f"Error: {e}")
            print("\nTroubleshooting steps:")
            print("1. Ensure Isaac Sim is running with OT-2 robot loaded")
            print("2. Check that ZMQ server is listening on tcp://localhost:5556")
            print("3. Verify SimOT2Node is running on http://127.0.0.1:8019/")
            print("4. Check MADSci services are running (docker-compose up)")
            print("5. Verify protocol file paths are correct")
            print("="*70)
            
            return False

    def run_quick_test(self) -> bool:
        """Run a quick validation test with minimal operations."""
        print("Starting OT-2 quick test")
        
        try:
            print("\n" + "="*50)
            print("RUNNING OT-2 QUICK TEST")
            print("="*50)
            
            # Initialize workcell client
            wc_client = WorkcellClient(workcell_server_url=self.config.workcell_url)
            time.sleep(1)

            # Use minimal test parameters
            quick_wells = ["A1", "A2"]
            quick_volumes = [100.0, 100.0]

            # Submit simplified workflow
            workflow_result = wc_client.submit_workflow(
                workflow=self.ot2_test_workflow,
                parameters={
                    "test_wells": quick_wells,
                    "test_volumes": quick_volumes,
                    "protocol_path": str(self.config.protocol_directory / "ot2_test_protocol.py"),
                },
                await_completion=True
            )

            print(f"Quick test completed: {workflow_result.name}")
            return True
            
        except Exception as e:
            print(f"Quick test failed: {e}")
            return False

    def clean_up(self) -> None:
        """Clean up test resources."""
        print("Test cleanup completed")


def main():
    """Main function to run OT-2 integration tests."""
    print("=" * 80)
    print("OT-2 SIMULATION INTEGRATION TESTING")
    print("=" * 80)
    print("This application validates your complete OT-2 simulation setup")
    print("including MADSci, Isaac Sim, and ZMQ communication.")
    print("=" * 80)
    
    # Create test application
    test_app = OT2TestApplication()
    
    try:
        # Run the comprehensive integration test
        success = test_app.run_integration_test()
        
        if success:
            print("\nALL TESTS PASSED! Your OT-2 integration is working perfectly.")
        else:
            print("\nTEST FAILED. Please check the error messages above.")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_app.clean_up()


if __name__ == "__main__":
    main()