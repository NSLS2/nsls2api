import asyncio
import datetime

from nsls2api.infrastructure import mongodb_setup
from nsls2api.infrastructure.config import get_settings
from nsls2api.models.beamlines import Beamline, ServiceAccounts
from nsls2api.services import pass_service

settings = get_settings()

# CHANGE THIS TO THE BEAMLINE YOU WANT TO UPDATE
BEAMLINE_NAME = "TLA"  # Example: "HXN", "CDI", "AMX", etc.


async def main():
    # Initialize Beanie
    await mongodb_setup.init_connection(settings.mongodb_dsn)

    pass_resources = await pass_service.get_pass_resources()
    pass_ids = [r["ID"] for r in pass_resources if r["Code"] == BEAMLINE_NAME]

    if not pass_ids:
        raise KeyError(f"No pass ID was found for {BEAMLINE_NAME}")

    if len(pass_ids) > 1:
        raise ValueError(f"Multiple pass IDs found for {BEAMLINE_NAME}: {pass_ids}")

    beamline = await Beamline.find_one(Beamline.pass_id == str(pass_ids[0]))
    if not beamline:
        raise KeyError(f"No beamline found with pass_id {pass_ids[0]}") 

    print("Current beamline:")
    print(beamline)

    # This is an example of updating the service accounts for the beamline.
    # Change these values to suit your needs.
    beamline.service_accounts = ServiceAccounts(
        ioc="softioc-tla-1",
        epics_services="epics-services-tla",
        workflow="workflow-tla",
        bluesky="bluesky-tla",
        operator="xf99id",
        lsdc=None
    )

    # INCLUDE ADDITIONAL CHANGES TO THE BEAMLINE OBJECT HERE AS NEEDED
    # Example: beamline.long_name = "Repurposed Beamline"
    #      or: beamline.port = "99-BM"
    # etc. or: beamline.network_locations = "xf99bm1"

    beamline.last_updated = datetime.datetime.now()

    print("New values to be updated for the beamline:", beamline.name)
    print(beamline)

    # Uncomment the line below to actually save the changes to the database
    # await beamline.save()

if __name__ == "__main__":
    asyncio.run(main())
