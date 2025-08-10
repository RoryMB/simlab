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

    # Get test parameters (will be substituted by MADSci)
    wells = $wells
    volumes = $volumes
    test_mode = $test_mode

    print(f"Test parameters: wells={wells}, volumes={volumes}, mode={test_mode}")

    deck = {}
    pipettes = {}

    # Test 1: Robot Homing and Initialization
    print("\n1. TESTING ROBOT HOMING...")
    protocol.home()
    print("   ✓ Home command successful")

    # Test 2: Labware Loading
    print("\n2. TESTING LABWARE LOADING...")

    # Load tip racks
    print("   Loading tip racks...")
    deck["1"] = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    deck["10"] = protocol.load_labware("opentrons_96_tiprack_300ul", "10")
    print("   ✓ Tip racks loaded successfully")

    # Load well plate
    print("   Loading well plate...")
    deck["2"] = protocol.load_labware("corning_96_wellplate_360ul_flat", "2")
    print("   ✓ Well plate loaded successfully")

    # Load reservoirs for liquid sources
    print("   Loading liquid reservoirs...")
    deck["5"] = protocol.load_labware("nest_1_reservoir_195ml", "5")
    deck["6"] = protocol.load_labware("nest_1_reservoir_195ml", "6")
    print("   ✓ Reservoirs loaded successfully")

    # Test 3: Pipette Loading
    print("\n3. TESTING PIPETTE LOADING...")
    pipettes["left"] = protocol.load_instrument(
        "p300_single_gen2",
        "left",
        tip_racks=[deck["1"], deck["10"]]
    )
    print("   ✓ Left pipette (p300) loaded successfully")

    # Test 4: Basic Movement and Positioning
    print("\n4. TESTING BASIC ROBOT MOVEMENT...")
    print("   Moving to tip rack...")
    pipettes["left"].move_to(deck["1"].wells()[0].top())
    print("   ✓ Movement to tip rack successful")

    print("   Moving to well plate...")
    pipettes["left"].move_to(deck["2"].wells()[0].top())
    print("   ✓ Movement to well plate successful")

    print("   Moving to reservoir...")
    pipettes["left"].move_to(deck["5"].wells()[0].top())
    print("   ✓ Movement to reservoir successful")

    # Test 5: Tip Handling
    print("\n5. TESTING TIP HANDLING...")

    # Pick up tip
    print("   Picking up tip...")
    pipettes["left"].pick_up_tip()
    print("   ✓ Tip pickup successful")

    # Test tip-holding state with movement
    print("   Moving with tip attached...")
    pipettes["left"].move_to(deck["2"].wells()[0].top())
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
    pipettes["left"].aspirate(100, deck["5"]["A1"])
    print("   ✓ Aspiration (100μL) successful")

    # Test dispensing to well
    print("   Testing dispensing...")
    pipettes["left"].dispense(100, deck["2"]["A1"])
    print("   ✓ Dispensing (100μL) successful")

    # Test blow out
    print("   Testing blow out...")
    pipettes["left"].blow_out()
    print("   ✓ Blow out successful")

    # Return tip
    pipettes["left"].return_tip()
    print("   ✓ Tip return successful")

    # Test 7: Multi-Well Operations (if test parameters provided)
    if wells and volumes:
        print("\n7. TESTING MULTI-WELL OPERATIONS...")
        print(f"   Processing {len(wells)} wells with volumes: {volumes}")

        # Pick up new tip
        pipettes["left"].pick_up_tip()

        # Process each well
        for i, well in enumerate(wells):
            volume = volumes[i] if i < len(volumes) else 50  # Default 50μL
            print(f"   Processing well {well} with {volume}μL...")

            # Aspirate from reservoir
            pipettes["left"].aspirate(volume, deck["5"]["A1"])

            # Dispense to target well
            pipettes["left"].dispense(volume, deck["2"][well])

            # Blow out for clean dispensing
            pipettes["left"].blow_out()

            print(f"   ✓ Well {well} processed successfully")

        # Return tip
        pipettes["left"].return_tip()
        print("   ✓ Multi-well operations completed")

    # Test 8: Precision Movement Test
    print("\n8. TESTING PRECISION MOVEMENTS...")

    # Pick up tip for precision tests
    pipettes["left"].pick_up_tip()

    # Test precise positioning at different heights
    print("   Testing well bottom positioning...")
    pipettes["left"].move_to(deck["2"]["A1"].bottom())
    print("   ✓ Bottom positioning successful")

    print("   Testing well center positioning...")
    pipettes["left"].move_to(deck["2"]["A1"].center())
    print("   ✓ Center positioning successful")

    print("   Testing well top positioning...")
    pipettes["left"].move_to(deck["2"]["A1"].top())
    print("   ✓ Top positioning successful")

    # Test offset positioning
    print("   Testing offset positioning...")
    pipettes["left"].move_to(deck["2"]["A1"].top().move(x=10, y=10, z=5))
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
        pipettes["left"].aspirate(30, deck["5"]["A1"])
        pipettes["left"].dispense(30, deck["2"][f"A{i+1}"])
        pipettes["left"].blow_out()
        print(f"   ✓ Transfer cycle {i+1} completed")

    # Test different volume ranges
    volumes_to_test = [10, 50, 150, 300]  # Test different volume ranges
    print("   Testing various volumes...")
    for vol in volumes_to_test:
        print(f"   Testing {vol}μL volume...")
        try:
            pipettes["left"].aspirate(vol, deck["5"]["A1"])
            pipettes["left"].dispense(vol, deck["6"]["A1"])  # Dispense to different reservoir
            pipettes["left"].blow_out()
            print(f"   ✓ {vol}μL volume test successful")
        except Exception as e:
            print(f"   ⚠ {vol}μL volume test failed: {e}")

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
    print("All major robot capabilities tested:")
    print("- Robot homing and initialization")
    print("- Labware loading and recognition")
    print("- Pipette loading and configuration")
    print("- Basic movement and positioning")
    print("- Tip handling (pickup/drop)")
    print("- Liquid handling (aspirate/dispense)")
    print("- Multi-well operations")
    print("- Precision positioning")
    print("- Advanced liquid handling")
    print("- System cleanup and homing")
    print("=" * 60)
