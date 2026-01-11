import sys
import time
from pathlib import Path
from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Asset
from madsci.common.types.workflow_types import WorkflowDefinition

# --- Configuration ---
WORKCELL_URL = "http://localhost:8015"
RESOURCE_URL = "http://localhost:8013"
WORKFLOW_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cleanup_test_workflow.yaml")

def setup_comprehensive_initial_state(rc: ResourceClient, wc: WorkcellClient):
    """Ensures the lab is in the correct state to run the multi-robot cleanup workflow."""
    print("=" * 80)
    print("SETTING UP COMPREHENSIVE MULTI-ROBOT LAB STATE")
    print("=" * 80)
    print("Setting up initial state for PF400, UR5e, and OT2 integration test...")

    locations = wc.get_locations()
    print(f"Found {len(locations)} locations in workcell:")
    for loc in locations:
        print(f"  - {loc.location_name}: {loc.description}")

    # Setup for UR5e - needs plates at location_1 and location_2
    print("\n--- Setting up UR5e test state ---")
    location_1 = next((loc for loc in locations if loc.location_name == "location_1"), None)
    location_2 = next((loc for loc in locations if loc.location_name == "location_2"), None)

    if not location_1 or not location_1.resource_id:
        raise Exception("Could not find 'location_1' or its resource_id. UR5e test setup failed.")
    if not location_2 or not location_2.resource_id:
        raise Exception("Could not find 'location_2' or its resource_id. UR5e test setup failed.")

    print(f"Found UR5e locations: location_1 ({location_1.resource_id}), location_2 ({location_2.resource_id})")

    # Create plate for UR5e transfer test
    ur5e_plate = Asset(resource_name="ur5e_test_plate", resource_class="well_plate")
    ur5e_plate = rc.add_or_update_resource(ur5e_plate)
    print(f"Created UR5e test plate: {ur5e_plate.resource_name} ({ur5e_plate.resource_id})")

    # Place plate at location_1 for UR5e transfer
    rc.push(resource=location_1.resource_id, child=ur5e_plate.resource_id)
    print(f"Placed UR5e plate at location_1 for transfer test")

    # Setup for PF400 - needs plates and special locations
    print("\n--- Setting up PF400 test state ---")
    
    # Find reliable PF400 locations (from pf400_test_workcell.yaml)
    platform1 = next((loc for loc in locations if loc.location_name == "platform1"), None)
    
    if not platform1 or not platform1.resource_id:
        raise Exception("Could not find 'platform1' or its resource_id. PF400 test setup failed.")
    
    print(f"Found PF400 platform1 location with resource ID: {platform1.resource_id}")
    
    # Verify all required PF400 locations exist
    required_pf400_locations = ["platform1", "platform2", "high_position", "approach_position"]
    for loc_name in required_pf400_locations:
        loc = next((loc for loc in locations if loc.location_name == loc_name), None)
        if not loc:
            raise Exception(f"Required PF400 location '{loc_name}' not found in workcell")
        print(f"✓ Found required PF400 location: {loc_name}")

    # Create microplate for PF400 test
    pf400_plate = Asset(resource_name="pf400_test_microplate", resource_class="microplate")
    pf400_plate = rc.add_or_update_resource(pf400_plate)
    print(f"Created PF400 test plate: {pf400_plate.resource_name} ({pf400_plate.resource_id})")

    # Place microplate at platform1 for PF400 transfer
    rc.push(resource=platform1.resource_id, child=pf400_plate.resource_id)
    print(f"Placed PF400 microplate at platform1")

    # Setup for OT2 - verify OT2-specific locations exist
    print("\n--- Setting up OT2 test state ---")
    
    # OT2 doesn't need physical plates placed since it uses its own protocol system
    # Just verify that OT2 locations exist (if any are defined)
    ot2_locations = [loc for loc in locations if "ot2" in loc.location_name.lower()]
    if ot2_locations:
        print(f"Found {len(ot2_locations)} OT2-specific locations:")
        for loc in ot2_locations:
            print(f"  - {loc.location_name}")
    else:
        print("No OT2-specific locations found (OT2 will use its internal deck system)")

    print("\n" + "=" * 80)
    print("MULTI-ROBOT LAB SETUP COMPLETE")
    print("=" * 80)
    print("✓ UR5e: Plate ready for transfer between location_1 and location_2")
    print("✓ PF400: Microplate ready for manipulation operations")
    print("✓ OT2: Protocol system ready for comprehensive testing")
    print("=" * 80)

def main():
    """Main function to set up multi-robot test state and submit the comprehensive workflow."""
    print("=" * 100)
    print("MULTI-ROBOT INTEGRATION TEST - CLEANUP VALIDATION")
    print("=" * 100)
    print("Testing PF400, UR5e, and OT2 integration after code cleanup...")
    print("This test validates that all robots work correctly with MADSci and Isaac Sim.")
    print("=" * 100)

    print("\nInitializing MADSci clients...")
    wc_client = WorkcellClient(workcell_server_url=WORKCELL_URL)
    rc_client = ResourceClient(url=RESOURCE_URL)

    print("Waiting for services to be ready...")
    time.sleep(5)

    # Setup initial state for all robots
    setup_comprehensive_initial_state(rc_client, wc_client)

    # Load and validate the workflow definition
    print(f"\nLoading multi-robot workflow definition from: {WORKFLOW_PATH}")
    if not WORKFLOW_PATH.exists():
        raise FileNotFoundError(f"Workflow file not found: {WORKFLOW_PATH}")
    
    workflow_definition = WorkflowDefinition.from_yaml(WORKFLOW_PATH)
    
    print(f"Loaded workflow: {workflow_definition.name}")
    print(f"Workflow contains {len(workflow_definition.steps)} test steps:")
    
    # Group steps by robot for better reporting
    robot_steps = {"sim_ur5e_1": [], "sim_pf400_1": [], "sim_ot2_1": []}
    for i, step in enumerate(workflow_definition.steps, 1):
        robot_name = step.node
        if robot_name in robot_steps:
            robot_steps[robot_name].append(f"{i}. {step.name} ({step.action})")
        else:
            print(f"  {i}. {step.name} ({step.action}) [Node: {robot_name}]")
    
    # Report steps by robot
    for robot, steps in robot_steps.items():
        if steps:
            print(f"\n{robot.upper()} TEST STEPS ({len(steps)} steps):")
            for step in steps:
                print(f"  {step}")

    # Submit the comprehensive workflow
    print(f"\n{'='*60}")
    print("SUBMITTING MULTI-ROBOT CLEANUP TEST WORKFLOW")
    print(f"{'='*60}")

    try:
        workflow_run = wc_client.submit_workflow(
            workflow=workflow_definition,
            parameters={
                "protocol_path": str(Path(__file__).parent / "ot2_test_protocol.py"),
            },
            await_completion=True,
        )

        print(f"\n{'='*60}")
        print("MULTI-ROBOT WORKFLOW EXECUTION COMPLETED")
        print(f"{'='*60}")
        print(f"Workflow '{workflow_run.name}' finished with status: {workflow_run.status.description}")
        
        # Detailed results by robot
        print("\nDETAILED RESULTS BY ROBOT:")
        print("-" * 60)
        
        robot_results = {"sim_ur5e_1": [], "sim_pf400_1": [], "sim_ot2_1": []}
        for i, step in enumerate(workflow_run.steps, 1):
            robot_name = step.node
            status = step.result.status if step.result else "PENDING"
            result_info = f"{i}. {step.name}: {status}"
            
            if robot_name in robot_results:
                robot_results[robot_name].append(result_info)
            else:
                print(f"UNKNOWN ROBOT - {result_info}")

        # Report results by robot
        for robot_name, results in robot_results.items():
            if results:
                robot_display = robot_name.replace("sim_", "").upper()
                print(f"\n{robot_display} RESULTS:")
                for result in results:
                    status_indicator = "✓" if "COMPLETED" in result else "✗" if "FAILED" in result else "⚠"
                    print(f"  {status_indicator} {result}")

        # Overall assessment
        print(f"\n{'='*60}")
        if workflow_run.status.description == "COMPLETED":
            print("🎉 MULTI-ROBOT INTEGRATION TEST PASSED!")
            print("{'='*60}")
            print("All robots are working correctly after the cleanup:")
            print("✓ UR5e robot: Communication and transfer operations working")
            print("✓ PF400 robot: Communication and manipulation operations working") 
            print("✓ OT2 robot: Communication and protocol execution working")
            print("✓ MADSci coordination: Multi-robot workflow execution working")
            print("✓ Isaac Sim integration: ZMQ communication working")
            print("\nYour cleanup was successful! The system is ready for use.")
        else:
            print("❌ MULTI-ROBOT INTEGRATION TEST FAILED")
            print("{'='*60}")
            print(f"Overall status: {workflow_run.status.description}")
            print("\nTROUBLESHOoting needed. Check individual robot results above.")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n{'='*60}")
        print("❌ CRITICAL ERROR DURING WORKFLOW EXECUTION")
        print(f"{'='*60}")
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Print detailed error information
        import traceback
        print(f"\nDetailed error trace:")
        traceback.print_exc()
        
        print(f"\n{'='*60}")
        print("TROUBLESHOOTING GUIDE")
        print(f"{'='*60}")
        print("1. ISAAC SIM ISSUES:")
        print("   - Ensure Isaac Sim is running with run_cleanup.py")
        print("   - Verify all 3 robots are loaded (UR5e, PF400, OT2)")
        print("   - Check ZMQ servers are listening:")
        print("     * UR5e on port 5555")
        print("     * OT2 on port 5556") 
        print("     * PF400 on port 5557")
        print("")
        print("2. MADSCI SERVICES:")
        print("   - Check MADSci services: cd projects/<project>/madsci && ./run_madsci.sh")
        print("   - Verify all robot nodes are running:")
        print("     * UR5e node: cd core/robots/ur5e && ./run_node_ur5e.sh (http://127.0.0.1:8018/)")
        print("     * PF400 node: cd core/robots/pf400 && ./run_node_pf400.sh (http://127.0.0.1:8020/)")
        print("     * OT2 node: cd core/robots/ot2 && ./run_node_ot2.sh (http://127.0.0.1:8019/)")
        print("   - Check workcell manager: http://localhost:8015")
        print("")
        print("3. CONFIGURATION:")
        print("   - Verify workcell.yaml contains all 3 robots")
        print("   - Check workflow file:", WORKFLOW_PATH)
        print("   - Verify protocol file: ot2_test_protocol.py")
        print("")
        print("4. NETWORK:")
        print("   - Test connections: curl http://localhost:8015/health")
        print("   - Check robot node status pages")
        print(f"{'='*60}")

if __name__ == "__main__":
    main()