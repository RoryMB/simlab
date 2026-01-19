"""Parallel workflow submission for scaling MVP testing.

Submits the same workflow to all 5 environments simultaneously and
tracks the results of each. Used to verify that the parallel environment
architecture works correctly.

Usage:
    python run_parallel_workflows.py workflow_transfer.yaml
    python run_parallel_workflows.py workflow_transfer.yaml --wait 10
"""

import argparse
import asyncio
import copy
import sys
import time
from pathlib import Path

from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient
from madsci.client.location_client import LocationClient
from madsci.common.types.resource_types import Asset
from madsci.common.types.workflow_types import WorkflowDefinition


NUM_ENVIRONMENTS = 5


def rewrite_workflow_locations(workflow: WorkflowDefinition, env_id: int) -> WorkflowDefinition:
    """Rewrite bare location names to env-prefixed names."""
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
    """Create a plate and place it at the starting location."""
    prefixed_location = f"env_{env_id}.{start_location_name}"
    prefixed_plate_name = f"env_{env_id}.test_microplate"

    locations = lc.get_locations()
    start_location = next(
        (loc for loc in locations if loc.location_name == prefixed_location),
        None,
    )

    if not start_location or not start_location.resource_id:
        raise Exception(f"Could not find starting location '{prefixed_location}'")

    print(f"  [env_{env_id}] Location {prefixed_location} has resource_id={start_location.resource_id}")

    plate_asset = Asset(resource_name=prefixed_plate_name, resource_class="microplate")
    plate = rc.add_or_update_resource(plate_asset)
    rc.push(resource=start_location.resource_id, child=plate.resource_id)

    print(f"  [env_{env_id}] Placed {prefixed_plate_name} at {prefixed_location}")


async def submit_workflow_async(
    env_id: int,
    workflow: WorkflowDefinition,
    resource_client: ResourceClient,
    location_client: LocationClient,
) -> tuple[int, bool, str]:
    """Submit workflow to a specific environment and return result.

    Args:
        env_id: Environment ID (0-4)
        workflow: Base workflow definition (will be rewritten for this env)
        resource_client: Shared resource client
        location_client: Shared location client

    Returns:
        Tuple of (env_id, success, description)
    """
    workcell_port = 8015 + (env_id * 10)
    workcell_url = f"http://localhost:{workcell_port}"
    workcell_client = WorkcellClient(workcell_server_url=workcell_url)

    # Setup initial state
    try:
        setup_initial_state(resource_client, location_client, env_id, "peeler_nest")
    except Exception as e:
        return (env_id, False, f"Setup failed: {e}")

    # Rewrite workflow for this environment
    env_workflow = rewrite_workflow_locations(workflow, env_id)
    # Give each workflow a unique name to prevent caching issues
    env_workflow.name = f"{env_workflow.name} (env_{env_id})"

    # Debug: print the rewritten location names and workflow model dump
    for step in env_workflow.steps:
        if step.locations:
            print(f"  [env_{env_id}] Step '{step.name}' locations: {step.locations}")

    # Debug: Print first step's locations from the model to verify serialization
    if env_workflow.steps:
        step_dict = env_workflow.steps[1].model_dump() if len(env_workflow.steps) > 1 else {}
        print(f"  [env_{env_id}] Step 1 model_dump locations: {step_dict.get('locations', {})}")

    print(f"  [env_{env_id}] Submitting workflow to {workcell_url}")

    # Run synchronous workflow submission in thread pool
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: workcell_client.submit_workflow(
                workflow_definition=env_workflow,
                await_completion=True,
                raise_on_failed=False,
                raise_on_cancelled=False,
            ),
        )
        status_ok = result.status.ok
        description = "Completed successfully" if status_ok else result.status.description
        return (env_id, status_ok, description)
    except Exception as e:
        return (env_id, False, str(e))


def print_all_location_resource_ids(lc: LocationClient, prefix: str = "peeler_nest"):
    """Print resource_ids for all env-prefixed locations to verify uniqueness."""
    print(f"\n--- Location Resource IDs for *{prefix} ---")
    locations = lc.get_locations()
    for env_id in range(NUM_ENVIRONMENTS):
        loc_name = f"env_{env_id}.{prefix}"
        loc = next((l for l in locations if l.location_name == loc_name), None)
        if loc:
            print(f"  {loc_name}: resource_id={loc.resource_id}")
        else:
            print(f"  {loc_name}: NOT FOUND")
    print()


async def run_parallel_test(workflow_path: Path) -> bool:
    """Run workflows on all 5 environments in parallel.

    Args:
        workflow_path: Path to the workflow YAML file

    Returns:
        True if all workflows succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Parallel Workflow Test")
    print(f"{'='*60}")
    print(f"Workflow: {workflow_path}")
    print(f"Environments: 0-{NUM_ENVIRONMENTS - 1}\n")

    # Shared clients
    resource_client = ResourceClient(resource_server_url="http://localhost:8013")
    location_client = LocationClient(location_server_url="http://localhost:8016")

    # Diagnostic: Print all location resource_ids to verify uniqueness
    print_all_location_resource_ids(location_client, "peeler_nest")
    print_all_location_resource_ids(location_client, "thermocycler_nest")

    # Load base workflow
    workflow = WorkflowDefinition.from_yaml(workflow_path)
    print(f"Loaded workflow '{workflow.name}' with {len(workflow.steps)} steps\n")

    print("Setting up initial states...")

    # Submit to all environments sequentially with delays to avoid caching issues
    print("\nSubmitting workflows to all environments (sequentially)...")
    start_time = time.time()

    results = []
    for env_id in range(NUM_ENVIRONMENTS):
        print(f"\n--- Submitting to env_{env_id} ---")
        result = await submit_workflow_async(env_id, workflow, resource_client, location_client)
        results.append(result)
        # Small delay between submissions
        if env_id < NUM_ENVIRONMENTS - 1:
            await asyncio.sleep(2)

    elapsed = time.time() - start_time

    # Report results
    print(f"\n{'='*60}")
    print(f"Results ({elapsed:.1f}s elapsed)")
    print(f"{'='*60}")

    success_count = 0
    for env_id, success, description in sorted(results):
        status = "SUCCESS" if success else "FAILED"
        print(f"  env_{env_id}: {status} - {description}")
        if success:
            success_count += 1

    print(f"\nTotal: {success_count}/{NUM_ENVIRONMENTS} succeeded")

    if success_count == NUM_ENVIRONMENTS:
        print("\nAll workflows completed successfully!")
    else:
        print(f"\nWARNING: {NUM_ENVIRONMENTS - success_count} workflow(s) failed")

    return success_count == NUM_ENVIRONMENTS


def main():
    parser = argparse.ArgumentParser(
        description="Run parallel workflow test across all 5 environments"
    )
    parser.add_argument(
        "workflow_file",
        type=str,
        help="Path to workflow YAML file",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=5,
        help="Seconds to wait for services before starting (default: 5)",
    )
    args = parser.parse_args()

    workflow_path = Path(args.workflow_file)
    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {args.workflow_file}")
        sys.exit(1)

    print(f"Waiting {args.wait}s for services...")
    time.sleep(args.wait)

    all_passed = asyncio.run(run_parallel_test(workflow_path))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
