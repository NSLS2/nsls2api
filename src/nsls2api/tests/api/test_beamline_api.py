import pytest
from httpx import ASGITransport, AsyncClient

from nsls2api.main import app
from nsls2api.models.beamlines import Beamline, DirectoryList, ServiceAccounts


@pytest.mark.anyio
async def test_get_beamline_service_accounts():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/v1/beamline/zzz/service-accounts")
    assert response.status_code == 200

    response_json = response.json()
    # Make sure we can create a ServiceAccounts object from the response
    accounts = ServiceAccounts(**response_json)
    assert accounts.workflow == "testy-mctestface-workflow"
    assert accounts.ioc == "testy-mctestface-ioc"
    assert accounts.bluesky == "testy-mctestface-bluesky"
    assert accounts.epics_services == "testy-mctestface-epics-services"
    assert accounts.operator == "testy-mctestface-xf66id6"
    assert accounts.lsdc is None or accounts.lsdc == ""


@pytest.mark.anyio
async def test_get_beamline_lowercase():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/v1/beamline/zzz")

    response_json = response.json()
    assert response.status_code == 200

    # Make sure we can create a Beamline object from the response
    beamline = Beamline(**response_json)
    assert beamline.name == "ZZZ"


@pytest.mark.anyio
async def test_get_beamline_uppercase():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/v1/beamline/ZZZ")

    response_json = response.json()
    assert response.status_code == 200

    # Make sure we can create a Beamline object from the response
    beamline = Beamline(**response_json)
    assert beamline.name == "ZZZ"


@pytest.mark.anyio
async def test_get_beamline_directory_skeleton():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/v1/beamline/zzz/directory-skeleton")
    response_json = response.json()

    assert response.status_code == 200
    assert response_json["directory_count"] == 2

    # Make sure we can create a DirectorySkeleton object from the response
    directory_skeleton = DirectoryList(**response_json)
    assert directory_skeleton.directory_count == 2

    # Make sure we can create a DirectorySkeleton object from the response
    directory_skeleton = DirectoryList(**response_json)
    assert directory_skeleton.directory_count == 2


@pytest.mark.anyio
async def test_get_nonexistent_beamline():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/v1/beamline/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Beamline 'DOES-NOT-EXIST' does not exist"}


@pytest.mark.anyio
async def test_get_service_accounts_for_nonexistent_beamline():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/v1/beamline/does-not-exist/service-accounts")
    assert response.status_code == 404
    assert response.json() == {"detail": "Beamline 'DOES-NOT-EXIST' does not exist"}


@pytest.mark.anyio
async def test_get_directory_skeleton_for_nonexistent_beamline():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/v1/beamline/does-not-exist/directory-skeleton")
    assert response.status_code == 404
