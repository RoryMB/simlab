import time
from pathlib import Path
from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Asset
from madsci.common.types.workflow_types import WorkflowDefinition

# --- Configuration ---
WORKCELL_URL = "http://localhost:8015"
RESOURCE_URL = "http://localhost:8013"
WORKFLOW_PATH = Path("./madsci_sim_lab/transfer_workflow.yaml")

def setup_initial_state(rc: ResourceClient, wc: WorkcellClient):
    """Ensures the lab is in the correct state to run the workflow."""
    print("--- Setting up initial lab state ---")

    locations = wc.get_locations()
    location_1 = next((loc for loc in locations if loc.location_name == "location_1"), None)

    if not location_1 or not location_1.resource_id:
        raise Exception("Could not find 'location_1' or its resource_id. The workcell may still be initializing.")

    print(f"Found source location 'location_1' with resource ID: {location_1.resource_id}")

    plate_asset = Asset(resource_name="test_plate", resource_class="well_plate")
    plate = rc.add_or_update_resource(plate_asset)
    print(f"Created/updated asset: {plate.resource_name} ({plate.resource_id})")

    print(f"Placing '{plate.resource_name}' into '{location_1.location_name}'...")
    rc.push(resource=location_1.resource_id, child=plate.resource_id)
    print("--- Setup complete ---")


def main():
    """Main function to set up state and submit the workflow."""
    print("Initializing MADSci clients...")
    wc_client = WorkcellClient(workcell_server_url=WORKCELL_URL)
    rc_client = ResourceClient(url=RESOURCE_URL)

    print("Waiting for services to be ready...")
    time.sleep(5)

    setup_initial_state(rc_client, wc_client)

    # Following the canonical MADSci example pattern:
    # 1. Load the workflow definition from its YAML file into a Python object.
    print(f"\nLoading workflow definition from: {WORKFLOW_PATH}")
    workflow_definition = WorkflowDefinition.from_yaml(WORKFLOW_PATH)

    # 2. Submit the Python object to the workcell manager.
    # The client will handle resolving locations correctly when passed an object.
    print("Submitting workflow...")

    workflow_run = wc_client.submit_workflow(
        workflow=workflow_definition,
        await_completion=True,
    )

    print("\n--- Workflow Result ---")
    print(f"Workflow '{workflow_run.name}' finished with status: {workflow_run.status.description}")
    print(f"Final status: {workflow_run.steps[0].result.status}")


if __name__ == "__main__":
    main()