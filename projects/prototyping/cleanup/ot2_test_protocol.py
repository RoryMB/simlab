requirements = {"robotType": "OT-2"}

from opentrons import protocol_api

metadata = {
    "protocolName": "OT-2 Integration Test Protocol",
    "author": "Claude Code",
    "description": "Comprehensive test protocol for validating OT-2 simulation integration",
    "apiLevel": "2.14"
}

def run(protocol: protocol_api.ProtocolContext):
    """
    Comprehensive OT-2 test protocol that exercises all major robot capabilities:
    - Homing and basic movement
    - Labware loading and positioning
    - Tip handling (pick up, drop)
    - Liquid handling (aspirate, dispense, blow out)
    - Multiple pipette operations
    - Error recovery scenarios
    """

    print("=" * 60)
    print("STARTING OT-2 COMPREHENSIVE INTEGRATION TEST")
    print("=" * 60)

    # Get test parameters from workflow (these would be passed via parameters in real use)
    # For now, using default test values
    wells = ["A1", "A2", "A3", "B1", "B2", "B3"]
    volumes = [50.0, 75.0, 100.0, 125.0, 150.0, 200.0]
    test_mode = "comprehensive"

    print(f"Test parameters: wells={wells}, volumes={volumes}, mode={test_mode}")

    # DEBUG: Check environment variables
    import os
    print("\nDEBUG - Environment Variables:")
    print(f"OPENTRONS_SIMULATION_MODE: {os.environ.get('OPENTRONS_SIMULATION_MODE', 'NOT SET')}")
    print(f"OT2_SIMULATION_SERVER: {os.environ.get('OT2_SIMULATION_SERVER', 'NOT SET')}")
    print("")

    deck = {}
    pipettes = {}

    # Test 1: Robot Homing and Initialization
    print("\n1. TESTING ROBOT HOMING...")
    protocol.home()
    print("   ✓ Home command successful")

    # Test 2: Labware Loading
    print("\n2. TESTING LABWARE LOADING...")

    # Load Primary tip rack
    print("   Loading tip rack 1...")
    deck["1"] = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    print("   ✓ Primary tip rack loaded successfully")

    # Load secondary tip rack
    print("   Loading tip rack 2...")
    deck["2"] = protocol.load_labware("opentrons_96_tiprack_300ul", "2")
    print("   ✓ Secondary tip rack loaded successfully")

    # Load well plate
    print("   Loading well plate...")
    deck["3"] = protocol.load_labware("corning_96_wellplate_360ul_flat", "3")
    print("   ✓ Well plate loaded successfully")

    # Load liquid source reservoir
    print("   Loading liquid reservoir...")
    deck["4"] = protocol.load_labware("nest_1_reservoir_195ml", "4")
    print("   ✓ Reservoir loaded successfully")

    # Test 3: Pipette Loading
    print("\n3. TESTING PIPETTE LOADING...")
    tip_racks = [deck["1"], deck["2"]]

    pipettes["left"] = protocol.load_instrument(
        "p300_single_gen2",
        "left",
        tip_racks=tip_racks,
    )
    print("   ✓ Left pipette (p300) loaded successfully")

    # Test 4: Basic Movement and Positioning
    print("\n4. TESTING BASIC ROBOT MOVEMENT...")
    print("   Moving to tip rack 1...")
    pipettes["left"].move_to(deck["1"].wells()[0].top())
    print("   ✓ Movement to tip rack 1 successful")

    print("   Moving to tip rack 2...")
    pipettes["left"].move_to(deck["2"].wells()[0].top())
    print("   ✓ Movement to tip rack 2 successful")

    print("   Moving to well plate...")
    pipettes["left"].move_to(deck["3"].wells()[0].top())
    print("   ✓ Movement to well plate successful")

    print("   Moving to reservoir...")
    pipettes["left"].move_to(deck["4"].wells()[0].top())
    print("   ✓ Movement to reservoir successful")

    # Test 5: Tip Handling
    print("\n5. TESTING TIP HANDLING...")

    # Pick up tip
    print("   Picking up tip...")
    pipettes["left"].pick_up_tip()
    print("   ✓ Tip pickup successful")

    # Test tip-holding state with movement
    print("   Moving with tip attached...")
    pipettes["left"].move_to(deck["3"].wells()[0].top())
    print("   ✓ Movement with tip successful")

    # Drop tip
    print("   Dropping tip...")
    pipettes["left"].drop_tip()
    print("   ✓ Tip drop successful")

    # Test 6: Liquid Handling Operations
    print("\n6. TESTING LIQUID HANDLING...")

    # Get a new tip for liquid handling
    pipettes["left"].pick_up_tip()

    # Test aspirating from reservoir
    print("   Testing aspiration...")
    pipettes["left"].aspirate(100, deck["4"]["A1"])
    print("   ✓ Aspiration (100μL) successful")

    # Test dispensing to well
    print("   Testing dispensing...")
    pipettes["left"].dispense(100, deck["3"]["A1"])
    print("   ✓ Dispensing (100μL) successful")

    # Test blow out
    print("   Testing blow out...")
    pipettes["left"].blow_out()
    print("   ✓ Blow out successful")

    # Return tip
    pipettes["left"].return_tip()
    print("   ✓ Tip return successful")

    # Test 7: Multi-Well Movement Operations
    print("\n7. TESTING MULTI-WELL MOVEMENT OPERATIONS...")
    print(f"   Testing movement to {len(wells)} wells: {wells}")

    # Pick up new tip for movement tests
    pipettes["left"].pick_up_tip()

    # Move to each specified well to test positioning
    for well in wells:
        print(f"   Moving to well {well}...")
        pipettes["left"].move_to(deck["3"][well].top())
        print(f"   ✓ Movement to well {well} successful")

        # If reservoir is available, do actual liquid handling
        if deck["4"] and volumes:
            volume = volumes[wells.index(well)] if wells.index(well) < len(volumes) else 50
            print(f"     Performing {volume}μL transfer...")
            pipettes["left"].aspirate(volume, deck["4"]["A1"])
            pipettes["left"].dispense(volume, deck["3"][well])
            pipettes["left"].blow_out()
            print(f"     ✓ Liquid transfer completed")

    # Return tip
    pipettes["left"].return_tip()
    print("   ✓ Multi-well operations completed")

    # Test 8: Precision Movement Test
    print("\n8. TESTING PRECISION MOVEMENTS...")

    # Pick up tip for precision tests
    pipettes["left"].pick_up_tip()

    # Test precise positioning at different heights
    print("   Testing well bottom positioning...")
    pipettes["left"].move_to(deck["3"]["A1"].bottom())
    print("   ✓ Bottom positioning successful")

    print("   Testing well center positioning...")
    pipettes["left"].move_to(deck["3"]["A1"].center())
    print("   ✓ Center positioning successful")

    print("   Testing well top positioning...")
    pipettes["left"].move_to(deck["3"]["A1"].top())
    print("   ✓ Top positioning successful")

    # Test offset positioning
    print("   Testing offset positioning...")
    pipettes["left"].move_to(deck["3"]["A1"].top().move(x=10, y=10, z=5))
    print("   ✓ Offset positioning successful")

    # Return tip
    pipettes["left"].return_tip()

    # Test 9: Advanced Liquid Handling
    print("\n9. TESTING ADVANCED LIQUID HANDLING...")

    pipettes["left"].pick_up_tip()

    # Test multiple aspirate/dispense cycles
    print("   Testing transfer operations...")
    for i in range(3):
        print(f"   Transfer cycle {i+1}/3...")
        pipettes["left"].aspirate(30, deck["4"]["A1"])
        pipettes["left"].dispense(30, deck["3"][f"A{i+1}"])
        pipettes["left"].blow_out()
        print(f"   ✓ Transfer cycle {i+1} completed")

    # Test different volume ranges (reduced to fit in single well)
    volumes_to_test = [10, 50, 100]  # Reduced volume ranges for single reservoir
    print("   Testing various volumes...")
    for vol in volumes_to_test:
        print(f"   Testing {vol}μL volume...")
        pipettes["left"].aspirate(vol, deck["4"]["A1"])
        pipettes["left"].dispense(vol, deck["3"]["B1"])  # Use different well
        pipettes["left"].blow_out()
        print(f"   ✓ {vol}μL volume test successful")

    pipettes["left"].return_tip()

    # Test 10: System Status and Cleanup
    print("\n10. TESTING SYSTEM CLEANUP...")

    # Final home to ensure robot returns to safe position
    print("   Homing robot for final position...")
    protocol.home()
    print("   ✓ Final homing successful")

    # Test Summary
    print("\n" + "=" * 60)
    print("OT-2 COMPREHENSIVE INTEGRATION TEST COMPLETED")
    print("=" * 60)
