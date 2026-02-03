import asyncio

from nsls2api.infrastructure import mongodb_setup
from nsls2api.infrastructure.config import get_settings
from nsls2api.models.beamlines import Beamline, ServiceAccounts
from nsls2api.services import pass_service

settings = get_settings()

# CHANGE THIS TO THE BEAMLINE YOU WANT TO CREATE
BEAMLINE_NAME = "CDI"


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

    # Change only the values that need to be changed.
    beamline.service_accounts = ServiceAccounts(
        ioc="softioc-cdi",
        epics_services="epics-services-cdi",
        workflow="workflow-cdi",
        bluesky="bluesky-cdi",
        operator="xf09id1",
        lsdc=None
    )

    await beamline.save()  
    print("Updated service_accounts for beamline:", beamline.name)

if __name__ == "__main__":
    asyncio.run(main())
