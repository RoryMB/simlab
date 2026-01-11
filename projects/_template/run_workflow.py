"""Workflow Runner Template

This script submits a workflow to the MADSci workcell manager and monitors its execution.
Customize the setup_initial_state() function for your specific workflow requirements.

Usage:
    python run_workflow.py [workflow.yaml]
"""

import sys
import time
from pathlib import Path

from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient
from madsci.client.location_client import LocationClient
from madsci.common.types.resource_types import Asset
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.exceptions import WorkflowFailedError

# --- Configuration ---
# These URLs should match your MADSci configuration in madsci/config/.env
RESOURCE_SERVER_URL = "http://localhost:8013"
WORKCELL_SERVER_URL = "http://localhost:8015"
LOCATION_SERVER_URL = "http://localhost:8016"

# Default workflow file if none specified
WORKFLOW_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("workflow.yaml")


def setup_initial_state(
    rc: ResourceClient,
    wc: WorkcellClient,
    lc: LocationClient
) -> None:
    """Set up the initial state required for the workflow.

    Customize this function to:
    1. Create/update resources (plates, samples, etc.)
    2. Place resources at starting locations
    3. Verify required locations exist

    Args:
        rc: Resource client for managing assets
        wc: Workcell client for workflow submission
        lc: Location client for managing locations
    """
    print("--- Setting up workflow initial state ---")

    locations = lc.get_locations()

    # Example: Find the starting location for your workflow
    start_loc_name = "ot2bioalpha_deck1_wide"  # Customize this
    start_location = next(
        (loc for loc in locations if loc.location_name == start_loc_name),
        None
    )

    if not start_location or not start_location.resource_id:
        raise Exception(
            f"Could not find starting location '{start_loc_name}' or its resource_id. "
            "The workcell may still be initializing or config is missing."
        )

    print(f"Found starting location '{start_loc_name}' with resource ID: {start_location.resource_id}")

    # Example: Create a test plate resource
    plate_asset = Asset(resource_name="test_microplate", resource_class="microplate")
    plate = rc.add_or_update_resource(plate_asset)
    print(f"Created/updated asset: {plate.resource_name} ({plate.resource_id})")

    # Example: Place the plate at the starting location
    print(f"Placing '{plate.resource_name}' on {start_loc_name}...")
    rc.push(resource=start_location.resource_id, child=plate.resource_id)

    # Example: Verify required locations exist
    required_locations = [
        "ot2bioalpha_deck1_wide",
        "sealer_nest",
        # Add your workflow's required locations here
    ]

    print("\nVerifying location definitions...")
    missing_locs = []

    for loc_name in required_locations:
        loc = next((loc for loc in locations if loc.location_name == loc_name), None)
        if not loc:
            print(f"  Missing: {loc_name}")
            missing_locs.append(loc_name)
        else:
            print(f"  Found: {loc_name}")

    if missing_locs:
        raise Exception(
            f"Missing {len(missing_locs)} required locations in Workcell config: {missing_locs}"
        )

    print("--- Initial state setup complete ---")


def main() -> None:
    """Main function to set up state and submit the workflow."""
    print("Initializing MADSci clients...")
    rc_client = ResourceClient(resource_server_url=RESOURCE_SERVER_URL)
    wc_client = WorkcellClient(workcell_server_url=WORKCELL_SERVER_URL)
    lc_client = LocationClient(location_server_url=LOCATION_SERVER_URL)

    print("Waiting for services to be ready...")
    time.sleep(5)

    setup_initial_state(rc_client, wc_client, lc_client)

    # Load the workflow definition
    print(f"\nLoading workflow definition from: {WORKFLOW_PATH}")
    if not WORKFLOW_PATH.exists():
        print(f"Workflow file not found: {WORKFLOW_PATH}")
        sys.exit(1)

    workflow_definition = WorkflowDefinition.from_yaml(WORKFLOW_PATH)

    print(f"Workflow contains {len(workflow_definition.steps)} steps:")
    for i, step in enumerate(workflow_definition.steps, 1):
        print(f"  {i}. {step.name} ({step.action})")

    # Submit the workflow to the workcell manager
    print("\nSubmitting workflow...")

    try:
        workflow_run = wc_client.submit_workflow(
            workflow_definition=workflow_definition,
            # Add file inputs if your workflow uses them:
            # file_inputs={"ot2_protocol_script": Path("ot2.py")},
            await_completion=True,
            prompt_on_error=False,
        )
    except WorkflowFailedError as e:
        print(f"\nWorkflow Failed: {e}")
        return

    print("\n--- Workflow Result ---")
    print(f"Workflow '{workflow_run.name}' finished with status: {workflow_run.status.description}")

    # Print results for each step
    print("\nStep Results:")
    for i, step in enumerate(workflow_run.steps, 1):
        status = step.result.status if step.result else "PENDING"
        print(f"  {i}. {step.name}: {status}")
        if step.result and hasattr(step.result, 'errors') and step.result.errors:
            print(f"     Error: {step.result.errors}")

    if workflow_run.status.description == "Completed Successfully":
        print("\nWorkflow completed successfully!")
    else:
        print(f"\nWorkflow failed: {workflow_run.status.description}")


if __name__ == "__main__":
    main()
