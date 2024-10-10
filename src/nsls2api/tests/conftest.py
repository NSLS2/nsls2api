import asyncio
import pytest

from nsls2api.infrastructure.config import get_settings
from nsls2api.infrastructure.mongodb_setup import init_connection
from nsls2api import models
from nsls2api.models.beamlines import Beamline, ServiceAccounts
from nsls2api.models.facilities import Facility
from nsls2api.services.beamline_service import service_accounts


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.fixture(scope="session")
async def db():

    settings = get_settings()
    await init_connection(settings.mongodb_dsn.unicode_string())

    # Insert a beamline into the database
    beamline = Beamline(name="ZZZ", port="66-ID-6", long_name="Magical PyTest X-Ray Beamline",
                        alternative_name="66-ID", network_locations=["xf66id6"],
                        pass_name="Beamline 66-ID-6", pass_id="666666",
                        nsls2_redhat_satellite_location_name="Nowhere",
                        service_accounts=ServiceAccounts(ioc="testy-mctestface-ioc",
                                                         bluesky="testy-mctestface-bluesky",
                                                         epics_services="testy-mctestface-epics-services",
                                                         operator="testy-mctestface-xf66id6",
                                                         workflow="testy-mctestface-workflow")
                        )
    await beamline.insert()

    # Insert a facility into the database
    facility = Facility(name="NSLS-II", facility_id="nsls2",
                        fullname="National Synchrotron Light Source II",
                        pass_facility_id="NSLS-II")
    await facility.insert()

    yield

    # Cleanup the database collections
    for model in models.all_models:
        print(f"dropping {model}")
        await model.get_motor_collection().drop()
        await model.get_motor_collection().drop_indexes()