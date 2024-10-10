import pytest
from httpx import AsyncClient
from nsls2api.models.beamlines import ServiceAccounts, Beamline

async def test_get_beamline_service_accounts(test_client: AsyncClient):
    response = await test_client.get("/v1/beamline/zzz/service-accounts")
    response_json = response.json()
    assert response.status_code == 200

    # Make sure we can create a ServiceAccounts object from the response
    accounts = ServiceAccounts(**response_json)
    assert accounts.workflow == "testy-mctestface-workflow"
    assert accounts.ioc == "testy-mctestface-ioc"
    assert accounts.bluesky == "testy-mctestface-bluesky"
    assert accounts.epics_services == "testy-mctestface-epics-services"
    assert accounts.operator == "testy-mctestface-xf66id6"
    assert accounts.lsdc is None or accounts.lsdc == ""


async def test_get_beamline_lowercase(test_client: AsyncClient):
    response = await test_client.get("/v1/beamline/zzz")
    response_json = response.json()
    assert response.status_code == 200

    # Make sure we can create a Beamline object from the response
    beamline = Beamline(**response_json)
    assert beamline.name == "ZZZ"

async def test_get_beamline_uppercase(test_client: AsyncClient):
    response = await test_client.get("/v1/beamline/ZZZ")
    response_json = response.json()
    assert response.status_code == 200

    # Make sure we can create a Beamline object from the response
    beamline = Beamline(**response_json)
    assert beamline.name == "ZZZ"

async def test_get_beamline_directory_skeleton(test_client: AsyncClient):
    response = await test_client.get("/v1/beamline/zzz/directory-skeleton")
    response_json = response.json()
    assert response.status_code == 200
