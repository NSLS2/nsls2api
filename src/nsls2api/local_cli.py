"""
This is a VERY rough local cli app that needs completely replacing.
It is just here for now to test some functionality before I add the API and use a better CLI framework.
"""

import asyncio

from nsls2api.infrastructure import mongodb_setup
from nsls2api.services import beamline_service, facility_service, proposal_service


def print_header():
    pad = 30
    print("/" + "-" * pad + "\\")
    print("|" + " " * pad + "|")
    print("|      NSLS-II CLI v0.0.1 " + " " * (pad - 25) + "|")
    print("|" + " " * pad + "|")
    print("\\" + "-" * pad + "/")
    print()


async def summary():
    facility_count = await facility_service.facilities_count()
    beamline_count = await beamline_service.beamline_count()
    proposal_count = await proposal_service.proposal_count()

    print("NSLS-II API Stats")
    print(f"Facilities: {facility_count:,}")
    print(f"Beamlines: {beamline_count:,}")
    print(f"Proposals: {proposal_count:,}")
    print()


async def search_for_beamline():
    pass


async def search_for_proposal():
    print("Let's find that proposal for you")
    proposal_id = input("Enter the proposal ID that you want to find: ").strip()
    proposal = await proposal_service.proposal_by_id(str(proposal_id))
    if proposal:
        print(proposal)
    else:
        print(f"No proposal with ID {proposal_id} found.")


async def recently_updated_proposals():
    proposals = await proposal_service.recently_updated()
    for n, p in enumerate(proposals, start=1):
        print(f"{n}. {p.proposal_id} ({p.last_updated.date().isoformat()}): {p.title}")
    print()


async def main():
    print_header()
    await mongodb_setup.init_connection(
        mongodb_setup.create_connection_string("localhost", 27017, "nsls2core-test")
    )
    print()
    # await summary()

    while True:
        print("[s] Show summary statistics")
        print("[b] Search for a beamline")
        print("[p] Search for a proposal")
        print("[m] Most recently updated proposals")
        print("[x] Exit program")
        resp = input("Enter the character for your command: ").strip().lower()
        print("-" * 40)

        match resp:
            case "s":
                await summary()
            case "b":
                await search_for_beamline()
            case "p":
                await search_for_proposal()
            case "m":
                await recently_updated_proposals()
            case "x":
                break
            case _:
                print("Sorry, we don't understand that command.")

        print()  # give the output a little space


if __name__ == "__main__":
    asyncio.run(main())
