requirements = {"robotType": "OT-2"}

from opentrons import protocol_api


metadata = {
    "protocolName": "Rinse Plate Protocol",
    "author": "Abe astroka@anl.gov",
    "description": "Rinses the specified wells of a 96 well plate",
    "apiLevel": "2.12"
}

def run(protocol: protocol_api.ProtocolContext):

    deck = {}
    pipettes = {}



    ################
    # load labware #
    ################
    deck["2"] = protocol.load_labware("corning_96_wellplate_360ul_flat", "2")

    deck["5"] = protocol.load_labware("nest_1_reservoir_195ml", "5")

    deck["5"].set_offset(x=0.00, y=0.00, z=1.50)

    deck["4"] = protocol.load_labware("nest_1_reservoir_195ml", "4")

    deck["4"].set_offset(x=0.00, y=0.00, z=1.50)

    deck["7"] = protocol.load_labware("nest_1_reservoir_195ml", "7")

    deck["7"].set_offset(x=0.00, y=0.00, z=1.50)


    deck["8"] = protocol.load_labware("nest_1_reservoir_195ml", "8")


    deck["8"].set_offset(x=0.00, y=0.00, z=1.50)


    deck["9"] = protocol.load_labware("nest_1_reservoir_195ml", "9")


    deck["9"].set_offset(x=0.00, y=0.00, z=1.50)


    deck["10"] = protocol.load_labware("opentrons_96_tiprack_300ul", "10")


    deck["11"] = protocol.load_labware("opentrons_96_tiprack_300ul", "11")


    pipettes["left"] = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[deck["10"], deck["11"]])


    ####################
    # execute commands #
    ####################

    # Step one
    wells = $wells
    pipettes["left"].pick_up_tip()
    for well in wells:

            pipettes["left"].aspirate(275, deck["2"][well])

            pipettes["left"].dispense(275, deck["4"]["A1"])

            pipettes["left"].blow_out()

    pipettes["left"].return_tip()
    pipettes["left"].pick_up_tip()
    for well in wells:

            pipettes["left"].aspirate(275, deck["7"]["A1"])

            pipettes["left"].dispense(275, deck["2"][well])

            pipettes["left"].mix(3, 50, deck["2"][well])

            pipettes["left"].aspirate(275, deck["2"][well])

            pipettes["left"].dispense(275, deck["4"]["A1"])

            pipettes["left"].blow_out()

    pipettes["left"].return_tip()
