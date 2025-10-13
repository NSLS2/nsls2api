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
    if len(pass_ids) > 1:
        raise ValueError(f"Multiple pass IDs found for {BEAMLINE_NAME}: {pass_ids}")

    # CHANGE THESE VALUES TO SUIT YOUR NEEDS
    new_beamline = Beamline(
        name=BEAMLINE_NAME,
        long_name="Fancy New Beamline",
        alternative_name="99-ID",
        port="99-ID",
        nsls2_redhat_satellite_location_name="Beamlines/99-ID ABC",
        pass_id=str(pass_ids[0]),
        pass_name="Beamline 99-ID",
        network_locations="xf99id1",
        github_org="NSLS2",
        service_accounts=ServiceAccounts(
            ioc="softioc-abc",
            epics_services="epics-abc",
            workflow="workflow-abc",
            bluesky="bluesky-abc",
            operator="xf99id",
        ),
    )
    print(new_beamline)

    # Uncomment this line to actually insert the new beamline into the database
    # await new_beamline.insert()


if __name__ == "__main__":
    asyncio.run(main())
