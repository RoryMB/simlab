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
RESOURCE_SERVER_URL = "http://localhost:8013"
WORKCELL_SERVER_URL = "http://localhost:8015"
LOCATION_SERVER_URL = "http://localhost:8016"
# Default to your PCR workflow if no argument is provided
WORKFLOW_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("workflow.yaml")

def setup_pcr_initial_state(rc: ResourceClient, wc: WorkcellClient, lc: LocationClient):
    """Ensures the lab is in the correct state to run the PCR workflow."""
    print("--- Setting up PCR Workflow state ---")

    locations = lc.get_locations()

    # 1. Identify the starting location based on the workflow (OT-2 Deck)
    start_loc_name = "ot2bioalpha_deck1_wide"
    start_location = next((loc for loc in locations if loc.location_name == start_loc_name), None)

    if not start_location or not start_location.resource_id:
        raise Exception(f"Could not find starting location '{start_loc_name}' or its resource_id. "
                        "The workcell may still be initializing or config is missing.")

    print(f"Found starting location '{start_loc_name}' with resource ID: {start_location.resource_id}")

    # 2. Create/Update the test plate
    plate_asset = Asset(resource_name="test_microplate", resource_class="microplate")
    plate = rc.add_or_update_resource(plate_asset)
    print(f"Created/updated asset: {plate.resource_name} ({plate.resource_id})")

    # 3. Place the plate on the OT-2 deck to match Step 1/2 of workflow
    print(f"Placing '{plate.resource_name}' on {start_loc_name}...")
    rc.push(resource=start_location.resource_id, child=plate.resource_id)

    # 4. Verify all required locations and approach paths exist in Workcell
    required_locations = [
        "ot2bioalpha_deck1_wide",
        "exchange_deck_high_wide",
        "exchange_deck_high_narrow",
        "sealer_nest",
        "bio_biometra3_nest",
        "peeler_nest",
        "hidex_geraldine_high_nest"
    ]

    required_approaches = [
        "safe_path_ot2bioalpha",
        "safe_path_exchange",
        "safe_path_sealer",
        "safe_path_biometra3",
        "safe_path_peeler",
        "safe_path_hidex"
    ]

    print("\nVerifying location definitions...")
    missing_locs = []

    for loc_name in required_locations + required_approaches:
        loc = next((loc for loc in locations if loc.location_name == loc_name), None)
        if not loc:
            print(f"❌ Missing: {loc_name}")
            missing_locs.append(loc_name)
        else:
            print(f"✓ Found: {loc_name}")

    if missing_locs:
        raise Exception(f"Missing {len(missing_locs)} required locations in Workcell config: {missing_locs}")

    print("--- PCR Workflow setup complete ---")


def main():
    """Main function to set up test state and submit the workflow."""
    print("Initializing MADSci clients for PCR Workflow...")
    rc_client = ResourceClient(resource_server_url=RESOURCE_SERVER_URL)
    wc_client = WorkcellClient(workcell_server_url=WORKCELL_SERVER_URL)
    lc_client = LocationClient(location_server_url=LOCATION_SERVER_URL)

    print("Waiting for services to be ready...")
    time.sleep(5)

    setup_pcr_initial_state(rc_client, wc_client, lc_client)

    # Load the workflow definition
    print(f"\nLoading workflow definition from: {WORKFLOW_PATH}")
    if not WORKFLOW_PATH.exists():
        print(f"❌ Workflow file not found: {WORKFLOW_PATH}")
        sys.exit(1)

    workflow_definition = WorkflowDefinition.from_yaml(WORKFLOW_PATH)

    print(f"Workflow contains {len(workflow_definition.steps)} steps:")
    for i, step in enumerate(workflow_definition.steps, 1):
        print(f"  {i}. {step.name} ({step.action})")

    # Link the narrow and wide exchange deck locations to share the same resource
    print("\nLinking exchange deck locations to share resources...")
    wide_location = lc_client.get_location_by_name("exchange_deck_high_wide")
    narrow_location = lc_client.get_location_by_name("exchange_deck_high_narrow")

    if wide_location.resource_id:
        print(f"Linking Narrow Location ({narrow_location.location_id}) to Resource ({wide_location.resource_id})...")
        lc_client.attach_resource(
            location_id=narrow_location.location_id,
            resource_id=wide_location.resource_id
        )
        print("Exchange deck locations linked successfully")
    else:
        print("No resource currently at wide location, skipping link")

    # Submit the workflow to the workcell manager
    print("\nSubmitting PCR workflow...")

    try:
        workflow_run = wc_client.submit_workflow(
            workflow_definition=workflow_definition,
            file_inputs={"ot2_protocol_script": Path("ot2.py")},
            await_completion=True,
            prompt_on_error=False,
        )
    except WorkflowFailedError as e:
        print(f"\n❌ Workflow Failed: {e}")
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
        print("\n✅ PCR simulation workflow completed successfully!")
    else:
        print(f"\n❌ PCR simulation workflow failed: {workflow_run.status.description}")


if __name__ == "__main__":
    main()
