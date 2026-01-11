import os
import argparse
from pxr import Sdf, Ar

# --- ANSI Color Codes for clearer output ---
class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ==============================================================================
#  ACTION REQUIRED: REVIEW AND COMPLETE THIS RENAME MAP
# ==============================================================================
RENAME_MAP = {
    # Geometry files (.usdc)
    "solorail.usdc": "SOLO.usdc",
    "platecrane_ex.usdc": "PlateCraneEX.usdc",
    "platecrane_sciclops.usdc": "PlateCraneSciClops.usdc",
    "platecrane_exchange.usdc": "platecrane_exchange.usdc", # Assuming no rename
    "platecrane_stacks.usdc": "platecrane_stacks.usdc",     # Assuming no rename
    "ot2_pipette_single.usdc": "OT-2_pipette_single.usdc",
    "ot2.usdc": "OT-2.usdc",
    "2f-85.usdc": "2F-85.usdc",
    "2f-140.usdc": "2F-140.usdc",
    "hidex.usdc": "SenseMicroplateReader.usdc",
    "thermocycler.usdc": "Biometra.usdc",
    "pf400.usdc": "PF400.usdc",
    "liconic.usdc": "STX88.usdc",
    "sealer.usdc": "a4SSealer.usdc",
    "peeler.usdc": "XPeel.usdc",
    "mir250.usdc": "MiR250.usdc",  # <-- Added this critical mapping

    # Material files (.usda)
    "desk_top.usda": "desk_top.usda", # Self-mapping for path correction
    "bio_wall_yellow.usda": "bio_wall_yellow.usda",
    "bio_wall_white.usda": "bio_wall_white.usda",
    "bio_floor.usda": "bio_floor.usda",
    "rpl_wall_paint_purple.usda": "rpl_wall_paint_purple.usda",
    "rpl_wall_paint_gray.usda": "rpl_wall_paint_gray.usda",
    "rpl_wall_concrete_low.usda": "rpl_wall_concrete_low.usda",
    "rpl_wall_concrete_high.usda": "rpl_wall_concrete_high.usda",
    "rpl_pipe_orange.usda": "rpl_pipe_orange.usda",
    "rpl_floor.usda": "rpl_floor.usda",
    "rpl_electrical.usda": "rpl_electrical.usda",
    "rpl_duct_vent.usda": "rpl_duct_vent.usda",
    "rpl_duct.usda": "rpl_duct.usda",
    "rpl_column.usda": "rpl_column.usda",
    "rpl_ceiling.usda": "rpl_ceiling.usda",
    "rpl_bar_green.usda": "rpl_bar_green.usda",
    "vention_foot.usda": "vention_foot.usda",
    "vention_bracket.usda": "vention_bracket.usda",
    "vention_bar.usda": "vention_bar.usda",
    "platecrane_sciclops_white.usda": "white.usda", # Example of renaming and simplifying
    "ot2_plastic_black.usda": "plastic_black.usda",
    "ot2_metal_black.usda": "metal_black.usda",
    "ot2_button_blue.usda": "button_blue.usda",
    "thermocycler_red.usda": "red.usda",
    "pf400_white.usda": "white.usda",
    "pf400_metal.usda": "metal.usda",
    "sealer_screen.usda": "screen.usda",
    "sealer_purple.usda": "purple.usda",
    "sealer_frame_white.usda": "frame_white.usda",
    "peeler_screen.usda": "screen.usda",
    "peeler_glass.usda": "glass.usda",
    "peeler_body_gray.usda": "body_gray.usda",
    "peeler_body_blue.usda": "body_blue.usda",

    # Texture files
    "rpl_floor.jpg": "rpl_floor.jpg"
}
# ==============================================================================


def build_file_index(root_dir):
    """Walks the root directory and creates a map of every filename to a LIST of its absolute paths."""
    print(f"{colors.OKBLUE}Phase 1: Indexing all files in '{os.path.abspath(root_dir)}'...{colors.ENDC}")
    file_index = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename in ['.DS_Store']: continue
            abs_path = os.path.abspath(os.path.join(dirpath, filename))
            if filename not in file_index: file_index[filename] = []
            file_index[filename].append(abs_path)

    duplicates = {name: paths for name, paths in file_index.items() if len(paths) > 1}
    if duplicates:
        print(f"{colors.WARNING}Info: Found duplicate filenames. Proximity logic will be used.{colors.ENDC}")
    print(f"{colors.OKGREEN}Indexing complete. Found {len(file_index)} unique filenames.{colors.ENDC}\n")
    return file_index

def find_best_path(source_file_dir, target_filename, file_index):
    """Finds the 'closest' path for a target file from a list of candidates."""
    candidate_paths = file_index.get(target_filename)
    if not candidate_paths: return None
    if len(candidate_paths) == 1: return candidate_paths[0]
    return min(candidate_paths, key=lambda path: len(os.path.relpath(path, start=source_file_dir)))

def fix_references(root_dir, do_commit=False):
    """Scans for USD files and corrects their internal references."""
    file_index = build_file_index(root_dir)
    usd_extensions = ('.usd', '.usda', '.usdc')

    print(f"{colors.OKBLUE}Phase 2: Scanning USD files...{colors.ENDC}")
    if not do_commit:
        print(f"{colors.BOLD}{colors.HEADER}-- DRY RUN MODE: No files will be modified. --{colors.ENDC}\n")
    else:
        print(f"{colors.BOLD}{colors.FAIL}-- COMMIT MODE: Files WILL be modified! --{colors.ENDC}\n")

    total_files_scanned, total_refs_fixed, total_files_changed = 0, 0, 0

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.lower().endswith(usd_extensions): continue

            total_files_scanned += 1
            filepath = os.path.abspath(os.path.join(dirpath, filename))

            try:
                layer = Sdf.Layer.FindOrOpen(filepath)
                if not layer: continue

                changes_to_apply = {} # Using a dict to store old_path -> new_path

                def check_and_propose_fix(old_path):
                    """Checks a single path and adds a proposed fix to the list if needed."""
                    if not old_path or old_path in changes_to_apply: return
                    if old_path.startswith(('http:', 'https:')) or old_path.endswith('.mdl'): return

                    resolver = Ar.GetResolver()
                    context = Ar.DefaultResolverContext([os.path.dirname(filepath)])
                    with Ar.ResolverContextBinder(context):
                        # --- CRITICAL FIX HERE ---
                        # Get the string representation of the resolved path.
                        resolved_path_obj = resolver.Resolve(old_path)
                        resolved_path_str = resolved_path_obj.GetPathString() if resolved_path_obj else ""

                    if resolved_path_str and os.path.exists(resolved_path_str): return

                    original_target_filename = os.path.basename(old_path.replace('@', ''))
                    target_filename = RENAME_MAP.get(original_target_filename, original_target_filename)
                    best_target_path = find_best_path(os.path.dirname(filepath), target_filename, file_index)

                    if best_target_path:
                        new_rel_path = os.path.relpath(best_target_path, os.path.dirname(filepath)).replace('\\', '/')
                        if '@' in old_path: new_rel_path = f"@{new_rel_path}@"
                        if new_rel_path != old_path:
                            changes_to_apply[old_path] = new_rel_path
                    else:
                        changes_to_apply[old_path] = "NOT FOUND IN INDEX"

                # Process sublayers
                for sublayer_path in layer.subLayerPaths: check_and_propose_fix(sublayer_path)

                # Process all other specs using the robust callback method
                def process_spec_callback(path):
                    spec = layer.GetObjectAtPath(path)
                    if not isinstance(spec, Sdf.PrimSpec): return
                    if spec.referenceList.isExplicit:
                        for ref in spec.referenceList.GetAddedOrExplicitItems(): check_and_propose_fix(ref.assetPath)
                    if spec.payloadList.isExplicit:
                        for payload in spec.payloadList.GetAddedOrExplicitItems(): check_and_propose_fix(payload.assetPath)
                    for attr in spec.attributes:
                        if attr.typeName == Sdf.ValueTypeNames.Asset and attr.default: check_and_propose_fix(attr.default.path)

                layer.Traverse(Sdf.Path.absoluteRootPath, process_spec_callback)

                if changes_to_apply:
                    print(f"Inspecting: {colors.BOLD}{os.path.relpath(filepath, root_dir)}{colors.ENDC}")
                    made_change_this_file = False
                    for old, new in changes_to_apply.items():
                        print(f"  - {colors.WARNING}Stale Path: {old}{colors.ENDC}")
                        if new == "NOT FOUND IN INDEX":
                            print(f"  - {colors.FAIL}Proposed Fix: {new}{colors.ENDC}")
                        else:
                            print(f"  - {colors.OKGREEN}Proposed Fix: {new}{colors.ENDC}")
                            if do_commit:
                                if layer.UpdateCompositionAssetDependency(old, new):
                                    print(f"    {colors.OKBLUE}  -> Committed.{colors.ENDC}")
                                    total_refs_fixed += 1
                                    made_change_this_file = True
                                else:
                                    print(f"    {colors.FAIL}  -> FAILED to commit change.{colors.ENDC}")
                    if made_change_this_file:
                        total_files_changed += 1
                        layer.Save()
                    print("-" * 80)

            except Exception:
                import traceback
                print(f"{colors.FAIL}ERROR processing {filepath}:{colors.ENDC}")
                traceback.print_exc()

    print(f"\n{colors.HEADER}Scan Complete.{colors.ENDC}")
    print(f"  - Scanned {total_files_scanned} files.")
    if do_commit:
        print(f"  - Fixed {colors.BOLD}{total_refs_fixed}{colors.ENDC} references across {colors.BOLD}{total_files_changed}{colors.ENDC} files.")
    else:
        print(f"  - Dry run found potential issues. Re-run with '--commit' to apply fixes.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scans for and repairs broken USD file references.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('directory', type=str, help='The root directory to scan (e.g., "assets").')
    parser.add_argument('--commit', action='store_true', help='Apply the fixes. Without this flag, script is in dry-run mode.')
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"{colors.FAIL}Error: Directory not found at '{args.directory}'{colors.ENDC}")
    else:
        fix_references(args.directory, do_commit=args.commit)