"""Workflow submission script for the simple project.

Submits a workflow to the workcell manager and waits for completion.
Creates a test microplate at the starting location for transfer workflows.
"""

import sys
import time
from pathlib import Path

from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient
from madsci.client.location_client import LocationClient
from madsci.common.types.resource_types import Asset
from madsci.common.types.workflow_types import WorkflowDefinition

WORKCELL_SERVER_URL = "http://localhost:8015"
RESOURCE_SERVER_URL = "http://localhost:8013"
LOCATION_SERVER_URL = "http://localhost:8016"


def setup_initial_state(rc: ResourceClient, lc: LocationClient):
    """Create a test microplate and place it at the peeler nest."""
    print("--- Setting up initial state ---")

    locations = lc.get_locations()

    start_location = next(
        (loc for loc in locations if loc.location_name == "peeler_nest"),
        None,
    )

    if not start_location or not start_location.resource_id:
        raise Exception(
            "Could not find starting location 'peeler_nest' or its resource_id. "
            "The workcell may still be initializing."
        )

    print(f"Found 'peeler_nest' with resource ID: {start_location.resource_id}")

    plate_asset = Asset(resource_name="test_microplate", resource_class="microplate")
    plate = rc.add_or_update_resource(plate_asset)
    print(f"Created asset: {plate.resource_name} ({plate.resource_id})")

    print("Placing microplate at peeler_nest...")
    rc.push(resource=start_location.resource_id, child=plate.resource_id)

    print("--- Initial state ready ---\n")


def main():
    workflow_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("workflow.yaml")

    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {workflow_path}")
        sys.exit(1)

    print(f"Workflow file: {workflow_path}\n")

    workcell_client = WorkcellClient(workcell_server_url=WORKCELL_SERVER_URL)
    resource_client = ResourceClient(resource_server_url=RESOURCE_SERVER_URL)
    location_client = LocationClient(location_server_url=LOCATION_SERVER_URL)

    print("Waiting for services...")
    time.sleep(2)

    setup_initial_state(resource_client, location_client)

    print(f"Loading workflow from {workflow_path}...")
    workflow = WorkflowDefinition.from_yaml(workflow_path)
    print(f"Workflow '{workflow.name}' has {len(workflow.steps)} steps\n")

    print("Submitting workflow...")
    try:
        result = workcell_client.submit_workflow(
            workflow_definition=workflow,
            prompt_on_error=False,
        )
        print(f"\nWorkflow completed with status: {result.status}")
        if result.status.ok:
            print("Success!")
        else:
            print(f"Description: {result.status.description}")
            sys.exit(1)
    except Exception as e:
        print(f"\nWorkflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
