"""Workflow submission script for scaling-mvp project.

Submits workflows to environment-specific workcell managers with
auto-prefixing of location and resource names based on env_id.
"""

import argparse
import copy
import sys
import time
from pathlib import Path

from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient
from madsci.client.location_client import LocationClient
from madsci.common.types.resource_types import Asset
from madsci.common.types.workflow_types import WorkflowDefinition


def rewrite_workflow_locations(workflow: WorkflowDefinition, env_id: int) -> WorkflowDefinition:
    """Rewrite bare location names to env-prefixed names.

    Transforms location references like 'peeler_nest' to 'env_0.peeler_nest'
    based on the target environment.

    Args:
        workflow: Original workflow definition
        env_id: Environment ID for prefixing

    Returns:
        Modified workflow with prefixed location names
    """
    workflow_copy = copy.deepcopy(workflow)
    prefix = f"env_{env_id}."

    for step in workflow_copy.steps:
        if step.locations:
            for key, location_name in list(step.locations.items()):
                if isinstance(location_name, str) and not location_name.startswith("env_"):
                    step.locations[key] = f"{prefix}{location_name}"

    return workflow_copy


def setup_initial_state(
    rc: ResourceClient,
    lc: LocationClient,
    env_id: int,
    start_location_name: str,
):
    """Create a plate and place it at the starting location.

    Uses env-prefixed names for both resources and locations to ensure
    isolation between parallel environments.

    Args:
        rc: Resource client
        lc: Location client
        env_id: Environment ID for namespacing
        start_location_name: Base location name (will be prefixed with env_id)
    """
    print(f"--- Setting up initial state for env_{env_id} ---")

    # Prefix location and resource names with env_id
    prefixed_location = f"env_{env_id}.{start_location_name}"
    prefixed_plate_name = f"env_{env_id}.test_microplate"

    locations = lc.get_locations()

    # Find the prefixed starting location
    start_location = next(
        (loc for loc in locations if loc.location_name == prefixed_location),
        None,
    )

    if not start_location or not start_location.resource_id:
        raise Exception(
            f"Could not find starting location '{prefixed_location}' or its resource_id."
        )

    print(f"Found starting location '{prefixed_location}' with resource ID: {start_location.resource_id}")

    # Create the test plate with env-prefixed name
    plate_asset = Asset(resource_name=prefixed_plate_name, resource_class="microplate")
    plate = rc.add_or_update_resource(plate_asset)
    print(f"Created/updated asset: {plate.resource_name} ({plate.resource_id})")

    # Place the plate at the starting location
    print(f"Placing '{plate.resource_name}' on {prefixed_location}...")
    rc.push(resource=start_location.resource_id, child=plate.resource_id)

    print("--- Initial state setup complete ---\n")


def main():
    """Submit workflow to a specific workcell environment."""
    parser = argparse.ArgumentParser(description="Submit workflow to a workcell environment")
    parser.add_argument(
        "--env-id",
        type=int,
        default=0,
        help="Environment ID (0-4) to submit workflow to",
    )
    parser.add_argument(
        "workflow_file",
        type=str,
        help="Path to workflow YAML file",
    )
    args = parser.parse_args()

    # Validate env_id
    if args.env_id < 0 or args.env_id > 4:
        print(f"Error: env_id must be between 0 and 4, got {args.env_id}")
        sys.exit(1)

    # Calculate manager ports based on env_id
    # Port mapping: env_0=8015, env_1=8025, env_2=8035, env_3=8045, env_4=8055
    workcell_port = 8015 + (args.env_id * 10)
    workcell_url = f"http://localhost:{workcell_port}"

    # Shared managers (same for all environments)
    resource_url = "http://localhost:8013"
    location_url = "http://localhost:8016"

    print(f"\nSubmitting workflow to Environment {args.env_id}")
    print(f"Workcell Manager: {workcell_url}")
    print(f"Workflow file: {args.workflow_file}\n")

    # Create clients
    workcell_client = WorkcellClient(workcell_server_url=workcell_url)
    resource_client = ResourceClient(resource_server_url=resource_url)
    location_client = LocationClient(location_server_url=location_url)

    # Wait for services to be ready
    print("Waiting for services...")
    time.sleep(2)

    # Set up initial state with env-prefixed resources
    setup_initial_state(resource_client, location_client, args.env_id, "peeler_nest")

    # Load and rewrite workflow
    workflow_path = Path(args.workflow_file)
    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {args.workflow_file}")
        sys.exit(1)

    print(f"Loading workflow from {args.workflow_file}...")
    workflow = WorkflowDefinition.from_yaml(workflow_path)
    workflow = rewrite_workflow_locations(workflow, args.env_id)

    print(f"Workflow '{workflow.name}' has {len(workflow.steps)} steps")
    print(f"Location names rewritten with 'env_{args.env_id}.' prefix\n")

    # Submit workflow and wait for completion
    print("Submitting workflow...")
    try:
        result = workcell_client.submit_workflow(
            workflow_definition=workflow,
            prompt_on_error=False, # CRITICAL
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
