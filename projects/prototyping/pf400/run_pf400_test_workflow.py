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
WORKFLOW_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("pf400_test_workflow.yaml")

def setup_pf400_initial_state(rc: ResourceClient, wc: WorkcellClient):
    """Ensures the PF400 test lab is in the correct state to run the workflow."""
    print("--- Setting up PF400 test lab state ---")

    locations = wc.get_locations()
    platform1 = next((loc for loc in locations if loc.location_name == "platform1"), None)

    if not platform1 or not platform1.resource_id:
        raise Exception("Could not find 'platform1' or its resource_id. The workcell may still be initializing.")

    print(f"Found platform1 location with resource ID: {platform1.resource_id}")

    # Create a test plate for the PF400 to manipulate
    plate_asset = Asset(resource_name="test_microplate", resource_class="microplate")
    plate = rc.add_or_update_resource(plate_asset)
    print(f"Created/updated asset: {plate.resource_name} ({plate.resource_id})")

    # Place the plate on platform1 as the starting position
    print(f"Placing '{plate.resource_name}' on platform1...")
    rc.push(resource=platform1.resource_id, child=plate.resource_id)
    
    # Verify all required locations exist
    required_locations = ["platform1", "platform2", "high_position", "approach_position"]
    for loc_name in required_locations:
        loc = next((loc for loc in locations if loc.location_name == loc_name), None)
        if not loc:
            raise Exception(f"Required location '{loc_name}' not found in workcell")
        print(f"✓ Found required location: {loc_name}")
    
    print("--- PF400 setup complete ---")


def main():
    """Main function to set up PF400 test state and submit the workflow."""
    print("Initializing MADSci clients for PF400 testing...")
    wc_client = WorkcellClient(workcell_server_url=WORKCELL_URL)
    rc_client = ResourceClient(url=RESOURCE_URL)

    print("Waiting for services to be ready...")
    time.sleep(5)

    setup_pf400_initial_state(rc_client, wc_client)

    # Load the PF400 test workflow definition
    print(f"\nLoading PF400 workflow definition from: {WORKFLOW_PATH}")
    workflow_definition = WorkflowDefinition.from_yaml(WORKFLOW_PATH)
    
    print(f"Workflow contains {len(workflow_definition.steps)} steps:")
    for i, step in enumerate(workflow_definition.steps, 1):
        print(f"  {i}. {step.name} ({step.action})")

    # Submit the workflow to the workcell manager
    print("\nSubmitting PF400 test workflow...")
    
    workflow_run = wc_client.submit_workflow(
        workflow=workflow_definition,
        await_completion=True,
    )

    print("\n--- PF400 Workflow Result ---")
    print(f"Workflow '{workflow_run.name}' finished with status: {workflow_run.status.description}")
    
    # Print results for each step
    print("\nStep Results:")
    for i, step in enumerate(workflow_run.steps, 1):
        status = step.result.status if step.result else "PENDING"
        print(f"  {i}. {step.name}: {status}")
    
    if workflow_run.status.description == "COMPLETED":
        print("\n✅ PF400 integration test completed successfully!")
    else:
        print(f"\n❌ PF400 integration test failed: {workflow_run.status.description}")


if __name__ == "__main__":
    main()