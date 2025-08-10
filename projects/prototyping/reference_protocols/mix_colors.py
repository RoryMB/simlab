requirements = {"robotType": "OT-2"}

from opentrons import protocol_api


metadata = {
    "protocolName": "Color Mixing Protocol",
    "author": "Abe astroka@anl.gov",
    "description": "Mix colors in a 96 well plate",
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

    deck["6"] = protocol.load_labware("nest_1_reservoir_195ml", "6")

    deck["6"].set_offset(x=0.00, y=0.00, z=1.50)


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
    amounts = $amounts
    tubs = ["5", "6", "8", "9"]
    for index2, tub in enumerate(tubs):
        pipettes["left"].pick_up_tip()
        for index, well in enumerate(wells):

            pipettes["left"].aspirate(amounts[index][index2], deck[tub]["A1"])

            pipettes["left"].dispense(amounts[index][index2], deck["2"][well])

            pipettes["left"].blow_out()

        pipettes["left"].return_tip()
