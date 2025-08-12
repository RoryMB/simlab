requirements = {"robotType": "OT-2"}

from opentrons import protocol_api

metadata = {
    "protocolName": "OT-2 Movement Debug Test",
    "author": "Claude Code",
    "description": "Minimal protocol to test if robot movement commands reach Isaac Sim",
    "apiLevel": "2.14"
}

def run(protocol: protocol_api.ProtocolContext):
    """
    Minimal test protocol that focuses ONLY on robot movement to debug ZMQ communication.
    This strips away all the complexity to isolate the core movement issue.
    """
    
    print("=" * 50)
    print("OT-2 MOVEMENT DEBUG TEST STARTING")
    print("=" * 50)
    
    # DEBUG: Check environment variables and log to file
    import os
    print("\\nDEBUG - Environment Variables:")
    print(f"OPENTRONS_SIMULATION_MODE: {os.environ.get('OPENTRONS_SIMULATION_MODE', 'NOT SET')}")
    print(f"OT2_SIMULATION_SERVER: {os.environ.get('OT2_SIMULATION_SERVER', 'NOT SET')}")
    
    # Also log to a file to bypass subprocess stdout issues
    with open("/tmp/ot2_debug.log", "w") as f:
        f.write(f"OPENTRONS_SIMULATION_MODE: {os.environ.get('OPENTRONS_SIMULATION_MODE', 'NOT SET')}\\n")
        f.write(f"OT2_SIMULATION_SERVER: {os.environ.get('OT2_SIMULATION_SERVER', 'NOT SET')}\\n")
    
    print("")
    
    # Test 1: Simple home command
    print("\\n1. TESTING HOME COMMAND...")
    print("   Sending home() command...")
    protocol.home()
    print("   ✓ Home command completed")
    
    # Test 2: Load labware and pipette (minimal setup)
    print("\\n2. MINIMAL SETUP...")
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    well_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "2")
    pipette = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tip_rack])
    print("   ✓ Basic labware and pipette loaded")
    
    # Test 3: Single movement command
    print("\\n3. TESTING BASIC MOVEMENT...")
    print("   Moving to tip rack A1...")
    pipette.move_to(tip_rack.wells()[0].top())
    print("   ✓ Movement to tip rack completed")
    
    # Test 4: Another movement command  
    print("\\n4. TESTING SECOND MOVEMENT...")
    print("   Moving to well plate A1...")
    pipette.move_to(well_plate.wells()[0].top())
    print("   ✓ Movement to well plate completed")
    
    # Test 5: Return home
    print("\\n5. FINAL HOME...")
    print("   Sending final home() command...")
    protocol.home()
    print("   ✓ Final home completed")
    
    print("\\n" + "=" * 50)
    print("OT-2 MOVEMENT DEBUG TEST COMPLETED")
    print("If you don't see the robot move in Isaac Sim,")
    print("check the Isaac Sim console for ZMQ debug output.")
    print("=" * 50)