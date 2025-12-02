# usd_reference_scanner_v4.py

import os
from pxr import Sdf

def find_all_references_from_layer(layer):
    """
    Scans an Sdf.Layer and returns a set of all unique external file paths.
    This version adds type checking to handle different spec types during traversal.
    """
    found_paths = set()

    # 1. Get sublayers directly from the layer
    found_paths.update(layer.subLayerPaths)

    # 2. Define a callback function to process each spec
    def _process_spec(path):
        spec = layer.GetObjectAtPath(path)
        if not spec:
            return
        
        # --- THIS IS THE CRITICAL FIX ---
        # We only care about PrimSpecs, as they are the only ones that
        # can have references, payloads, and asset-path attributes.
        if not isinstance(spec, Sdf.PrimSpec):
            return

        prim_spec = spec

        # Check References
        if prim_spec.referenceList.isExplicit:
            for ref in prim_spec.referenceList.GetAddedOrExplicitItems():
                if ref.assetPath:
                    found_paths.add(ref.assetPath)
        
        # Check Payloads
        if prim_spec.payloadList.isExplicit:
            for payload in prim_spec.payloadList.GetAddedOrExplicitItems():
                if payload.assetPath:
                    found_paths.add(payload.assetPath)

        # Check for attributes of type 'asset' on this prim
        for attr_spec in prim_spec.attributes:
            if attr_spec.typeName == Sdf.ValueTypeNames.Asset:
                asset_path = attr_spec.default
                if asset_path and asset_path.path:
                    found_paths.add(asset_path.path)

    # 3. Traverse all specs using the callback function
    layer.Traverse(Sdf.Path.absoluteRootPath, _process_spec)
    
    return found_paths


def scan_directory(root_dir):
    """
    Recursively scans a directory for USD files and prints their references.
    """
    print(f"Starting scan in directory: {os.path.abspath(root_dir)}\n")
    usd_extensions = ('.usd', '.usda', '.usdc')

    for root, _, files in os.walk(root_dir):
        for filename in files:
            if not filename.lower().endswith(usd_extensions):
                continue
            
            filepath = os.path.join(root, filename)
            print(f"Inspecting: {os.path.relpath(filepath, root_dir)}")

            try:
                layer = Sdf.Layer.FindOrOpen(filepath)
                
                if not layer:
                    print("  \033[91m- ERROR: Could not open layer. File is likely corrupt or unreadable.\033[0m")
                    continue
                
                references = find_all_references_from_layer(layer)
                if not references:
                    print("  - (No external file references found)")
                else:
                    for ref_path in sorted(list(references)):
                        print(f"  - Ref: {ref_path}")

            except Exception as e:
                import traceback
                print(f"  \033[91m- ERROR: An unexpected exception occurred: {e}\033[0m")
                traceback.print_exc()
            
            print("-" * 80)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scan a directory for USD files and list their external references (Ultra-Compatible Version).")
    parser.add_argument('directory', type=str, help='The root directory to scan (e.g., "assets").')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found at '{args.directory}'")
    else:
        scan_directory(args.directory)