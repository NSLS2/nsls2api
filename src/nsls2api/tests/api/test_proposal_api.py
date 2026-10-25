import pytest
from httpx import ASGITransport, AsyncClient

from nsls2api.api.models.proposal_model import RecentProposalsList
from nsls2api.main import app
from nsls2api.models.proposals import Proposal

test_beamline_name = "ZZZ"


@pytest.mark.anyio
async def test_get_recent_proposals_with_null_title():
    await Proposal(
        proposal_id="271828",
        data_session="pass-271828",
        title=None,
        instruments=[test_beamline_name],
    ).insert()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/v1/proposals/recent/10?beamline={test_beamline_name.lower()}"
        )

    assert response.status_code == 200

    recent = RecentProposalsList(**response.json())
    by_id = {p.proposal_id: p for p in recent.proposals}
    assert "271828" in by_id
    assert by_id["271828"].title is None
