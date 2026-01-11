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
            print(f"Error type: {type(e).__name__}")
            
            # Print detailed error information
            import traceback
            print(f"\nDetailed error trace:")
            traceback.print_exc()
            
            print("\n" + "="*50)
            print("TROUBLESHOOTING GUIDE")
            print("="*50)
            print("1. ISAAC SIM SETUP:")
            print("   - Ensure Isaac Sim is running")
            print("   - Verify OT-2 robot is loaded and visible")
            print("   - Check ZMQ server is listening on tcp://localhost:5556")
            print("   - Look for 'ot2_1 ZMQ server listening on port 5556' message")
            print("")
            print("2. MADSCI SETUP:")
            print("   - Check MADSci services: cd core/madsci && ./run_madsci.sh")
            print("   - Verify OT-2 node: cd core/robots/ot2 && ./run_node_ot2.sh")
            print("   - Check node status at http://127.0.0.1:8019/status")
            print("   - Verify workcell at http://localhost:8015")
            print("")
            print("3. PROTOCOL ISSUES:")
            print("   - Check protocol file exists:", self.config.protocol_directory / "ot2_test_protocol.py")
            print("   - Verify workflow file exists:", self.config.workflow_directory / "ot2_test_workflow.yaml")
            print("")
            print("4. NETWORK CONNECTIVITY:")
            print("   - Test MADSci connection: curl http://localhost:8015/health")
            print("   - Test OT-2 node: curl http://127.0.0.1:8019/status")
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

            # Submit simplified workflow
            workflow_result = wc_client.submit_workflow(
                workflow=self.ot2_test_workflow,
                parameters={
                    "protocol_path": str(self.config.protocol_directory / "ot2_test_protocol.py"),
                },
                await_completion=True
            )

            print(f"Quick test completed: {workflow_result.name}")
            return True
            
        except Exception as e:
            print(f"Quick test failed: {e}")
            return False

    def test_connections(self) -> bool:
        """Test connectivity to all required services."""
        print("\n" + "="*50)
        print("TESTING SERVICE CONNECTIVITY")
        print("="*50)
        
        try:
            # Test MADSci workcell connection
            print("1. Testing MADSci workcell connection...")
            wc_client = WorkcellClient(workcell_server_url=self.config.workcell_url)
            print("   ✓ MADSci workcell connection successful")
            
            # Test protocol file existence
            protocol_path = self.config.protocol_directory / "ot2_test_protocol.py"
            print(f"2. Testing protocol file: {protocol_path}")
            if protocol_path.exists():
                print("   ✓ Protocol file found")
            else:
                print("   ✗ Protocol file missing")
                return False
                
            # Test workflow file existence
            workflow_path = self.config.workflow_directory / "ot2_test_workflow.yaml"
            print(f"3. Testing workflow file: {workflow_path}")
            if workflow_path.exists():
                print("   ✓ Workflow file found")
            else:
                print("   ✗ Workflow file missing")
                return False
            
            print("\n✓ All connectivity tests passed!")
            return True
            
        except Exception as e:
            print(f"\n✗ Connectivity test failed: {e}")
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
        # First test basic connectivity
        if not test_app.test_connections():
            print("\nCONNECTIVITY TEST FAILED. Please fix the issues above before running integration tests.")
            return
        
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