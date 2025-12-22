requirements = {"robotType": "OT-2"}

from opentrons import protocol_api

metadata = {
    'apiLevel': '2.14',
    'protocolName': 'Empty Protocol',
    'description': 'A dummy protocol for simulation testing',
    'author': 'Rory Butler'
}

def run(protocol: protocol_api.ProtocolContext):
    # Determine the API version from metadata
    # A simple comment or pass is sufficient for an empty run
    protocol.comment('Empty protocol')
