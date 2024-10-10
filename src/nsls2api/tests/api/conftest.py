import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from nsls2api.main import app
from nsls2api.models import facilities, jobs, apikeys, proposals, beamlines, cycles, proposal_types

@pytest.fixture(scope="session", autouse=True)
async def test_client(db):
    async with LifespanManager(app, startup_timeout=100, shutdown_timeout=100):
        server_name = "http://localhost"
        async with AsyncClient(transport=ASGITransport(app=app), base_url=server_name, follow_redirects=True) as client:
            yield client

#
# @pytest.fixture(autouse=True)
# async def clean_db(db):
#     all_models = [
#         facilities.Facility,
#         cycles.Cycle,
#         proposal_types.ProposalType,
#         beamlines.Beamline,
#         proposals.Proposal,
#         apikeys.ApiKey,
#         apikeys.ApiUser,
#         jobs.BackgroundJob,
#     ]
#     yield None
#
#     for model in all_models:
#         print(f"dropping {model}")
#         # await model.get_motor_collection().drop()
#         # await model.get_motor_collection().drop_indexes()
#


