import asyncio
import datetime

from nsls2api.infrastructure import mongodb_setup
from nsls2api.infrastructure.config import get_settings
from nsls2api.models.beamlines import Beamline, ServiceAccounts
from nsls2api.services import pass_service

settings = get_settings()

# CHANGE THIS TO THE BEAMLINE YOU WANT TO UPDATE
BEAMLINE_NAME = "TLA"


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

    print(beamline)

    # CHANGE THESE VALUES TO SUIT YOUR NEEDS.
    beamline.service_accounts = ServiceAccounts(
        ioc="softioc-tla",
        epics_services="epics-services-tla",
        workflow="workflow-tla",
        bluesky="bluesky-tla",
        operator="xf09id1",
        lsdc=None
    )

    print("Will update service_accounts for beamline:", beamline.name)

    beamline.last_updated = datetime.datetime.now()
    print(datetime.datetime.now())

    # Uncomment the line below to actually save the changes to the database
    # await beamline.save()

    print("Updated beamline")
    print(beamline)

if __name__ == "__main__":
    asyncio.run(main())
