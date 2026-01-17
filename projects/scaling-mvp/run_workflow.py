"""Workflow submission script for scaling-mvp project."""

import argparse
import sys

from madsci.client.workcell_client import WorkcellClient


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

    # Calculate workcell manager port based on env_id
    # Port mapping: env_0=8015, env_1=8025, env_2=8035, env_3=8045, env_4=8055
    workcell_port = 8015 + (args.env_id * 10)
    workcell_url = f"http://localhost:{workcell_port}"

    print(f"\nSubmitting workflow to Environment {args.env_id}")
    print(f"Workcell Manager: {workcell_url}")
    print(f"Workflow file: {args.workflow_file}\n")

    # Create workcell client
    workcell_client = WorkcellClient(workcell_server_url=workcell_url)

    # Submit workflow and wait for completion
    print("Submitting workflow...")
    try:
        result = workcell_client.submit_workflow(
            workflow_definition=args.workflow_file,
            await_completion=True,
            raise_on_failed=False,
            raise_on_cancelled=False,
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
