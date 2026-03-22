#!/usr/bin/env python3
"""
YAML Workflow Format Converter

Converts old WEI workflow format (flowdef-based) to new MADSci format (steps-based).

Features:
  - Separates location args from regular args
  - Renames modules to nodes via --module-map
  - Auto-generates parameters section from file references in steps

Usage:
    python wei_2_yaml.py input.yaml [output.yaml]
    python wei_2_yaml.py -q input.yaml [output.yaml]
    python wei_2_yaml.py --module-map map.yaml input.yaml [output.yaml]

Module map file format (YAML):
    biopf400: pf400
    bio_sealer: sealer
    ot2bioalpha: ot2
"""

import sys
import yaml
from pathlib import Path


LOCATION_KEYS = {'source', 'target', 'source_approach', 'target_approach'}


def load_module_map(map_path: str) -> dict[str, str]:
    """Load module-to-node name mapping from a YAML file."""
    with open(map_path, 'r') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Module map must be a YAML dictionary, got {type(data).__name__}")
    return data


def convert_step(old_step, module_map: dict[str, str] = None):
    """Convert a single step from old to new format."""
    if 'action' not in old_step:
        raise ValueError("Step missing 'action' field")
    if 'name' not in old_step:
        raise ValueError("Step missing 'name' field")
    if 'module' not in old_step:
        raise ValueError("Step missing 'module' field")

    module_name = old_step['module']
    node_name = module_map.get(module_name, module_name) if module_map else module_name

    new_step = {
        'name': old_step['name'],
        'node': node_name,
        'action': old_step['action'],
    }

    if 'args' in old_step:
        new_args = {}
        locations = {}

        for key, value in old_step['args'].items():
            if key in LOCATION_KEYS:
                locations[key] = value
            else:
                new_args[key] = value

        new_step['args'] = new_args
        if locations:
            new_step['locations'] = locations

    if 'files' in old_step:
        new_step['files'] = old_step['files']

    return new_step


def collect_file_parameters(steps: list[dict]) -> tuple[list[dict], list[dict]]:
    """Collect file references from steps and generate parameter declarations.

    For each unique file reference found in steps, creates a parameter
    declaration and replaces the literal filename with the parameter key.

    Returns:
        Tuple of (parameters list, updated steps list)
    """
    parameters = []
    seen_keys = set()

    for step in steps:
        if 'files' not in step:
            continue

        new_files = {}
        for arg_name, filename in step['files'].items():
            # Generate a parameter key from the arg name
            param_key = f"{arg_name}_script"

            if param_key not in seen_keys:
                seen_keys.add(param_key)
                parameters.append({
                    'key': param_key,
                    'parameter_type': 'file_input',
                    'description': f"{arg_name.replace('_', ' ').title()} file",
                })

            new_files[arg_name] = param_key

        step['files'] = new_files

    return parameters, steps


def convert_workflow(old_data, module_map: dict[str, str] = None, quiet: bool = False):
    """Convert old format workflow to new format."""
    if 'flowdef' not in old_data:
        raise ValueError("Missing 'flowdef' key")

    if not isinstance(old_data['flowdef'], list):
        raise ValueError("'flowdef' must be a list")

    if not quiet:
        if 'name' not in old_data:
            raise ValueError("Missing 'name' field")
        if 'author' not in old_data and 'info' not in old_data and 'version' not in old_data:
            raise ValueError("Missing all metadata fields (author, info, version)")

    new_data = {'name': old_data.get('name', 'Unnamed Workflow')}

    metadata = {}
    if 'author' in old_data:
        metadata['author'] = old_data['author']
    if 'info' in old_data:
        metadata['info'] = old_data['info']
    if 'version' in old_data:
        metadata['version'] = old_data['version']

    if metadata:
        new_data['metadata'] = metadata

    steps = [convert_step(step, module_map) for step in old_data['flowdef']]

    # Collect file parameters and update steps in place
    parameters, steps = collect_file_parameters(steps)
    if parameters:
        new_data['parameters'] = parameters

    new_data['steps'] = steps

    return new_data


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print(
            "Usage: python wei_2_yaml.py [-q] [--module-map map.yaml] input.yaml [output.yaml]",
            file=sys.stderr,
        )
        sys.exit(1)

    quiet = '-q' in sys.argv
    remaining = [arg for arg in sys.argv[1:] if arg != '-q']

    # Parse --module-map
    module_map = None
    if '--module-map' in remaining:
        idx = remaining.index('--module-map')
        if idx + 1 >= len(remaining):
            print("Error: --module-map requires a file path argument", file=sys.stderr)
            sys.exit(1)
        module_map = load_module_map(remaining[idx + 1])
        remaining = remaining[:idx] + remaining[idx + 2:]

    if not remaining:
        print("Error: no input file specified", file=sys.stderr)
        sys.exit(1)

    input_path = Path(remaining[0])
    output_path = Path(remaining[1]) if len(remaining) > 1 else None

    with open(input_path, 'r') as f:
        old_data = yaml.safe_load(f)

    new_data = convert_workflow(old_data, module_map=module_map, quiet=quiet)

    yaml_output = yaml.dump(
        new_data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )

    if output_path:
        with open(output_path, 'w') as f:
            f.write(yaml_output)
    else:
        print(yaml_output)


if __name__ == '__main__':
    main()
