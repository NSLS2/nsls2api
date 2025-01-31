from typing import Annotated

import fastapi
from fastapi import Depends, Query, HTTPException

from nsls2api.api.models.facility_model import FacilityName
from nsls2api.api.models.proposal_model import (
    CommissioningProposalsList,
    ProposalDirectoriesList,
    ProposalFullDetailsList,
    ProposalUser,
    ProposalUserList,
    RecentProposal,
    RecentProposalsList,
    SingleProposal,
)
from nsls2api.api.models.proposal_model import UsernamesList
from nsls2api.infrastructure.security import get_current_user
from nsls2api.services import proposal_service

router = fastapi.APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/proposals/recent/{count}", response_model=RecentProposalsList)
async def get_recent_proposals(count: int, beamline: str | None = None):
    count = max(1, count)

    proposals = await proposal_service.recently_updated(count, beamline=beamline)

    proposal_models = [
        RecentProposal(
            proposal_id=p.proposal_id,
            title=p.title,
            updated=p.last_updated,
            instruments=p.instruments,
        )
        for p in proposals
    ]
    model = RecentProposalsList(count=len(proposal_models), proposals=proposal_models)

    return model


@router.get("/proposals/commissioning", response_model=CommissioningProposalsList)
async def get_commissioning_proposals(
    beamline: str | None = None, facility: FacilityName | None = None
):
    try:
        proposals = await proposal_service.commissioning_proposals(
            beamline=beamline, facility_name=facility
        )
        if proposals is None:
            raise HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="No commissioning proposals found",
            )
    except LookupError as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=e.args[0]
        )
    except Exception as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}",
        )

    model = CommissioningProposalsList(
        count=len(proposals), commissioning_proposals=proposals
    )
    return model


@router.get(
    "/proposals/",
    response_model=ProposalFullDetailsList,
    description="Not fully functional yet.",
)
async def get_proposals(
    proposal_id: Annotated[list[str], Query()] = [],
    beamline: Annotated[list[str], Query()] = [],
    cycle: Annotated[list[str], Query()] = [],
    facility: Annotated[list[FacilityName], Query()] = [FacilityName.nsls2],
    page_size: int = 10,
    page: int = 1,
    include_directories: bool = False,
):
    proposal_list = await proposal_service.fetch_proposals(
        proposal_id=proposal_id,
        beamline=beamline,
        cycle=cycle,
        facility=facility,
        page_size=page_size,
        page=page,
        include_directories=include_directories,
    )

    response_model = {
        "proposals": proposal_list,
        "page_size": page_size,
        "page": page,
        "count": len(proposal_list),
    }

    return response_model


@router.get("/proposal/{proposal_id}", response_model=SingleProposal)
async def get_proposal(proposal_id: str):
    try:
        proposal = await proposal_service.proposal_by_id(proposal_id)
        if proposal is None:
            raise HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Proposal {proposal_id} not found",
            )
    except LookupError as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=e.args[0]
        )
    except Exception as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}",
        )

    response_model = SingleProposal(proposal=proposal)
    return response_model


@router.get("/proposal/{proposal_id}/users", response_model=ProposalUserList)
async def get_proposals_users(proposal_id: str):
    try:
        users = await proposal_service.fetch_users_on_proposal(proposal_id)
        if users is None:
            raise HTTPException(
                fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Users not found for proposal {proposal_id}",
            )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=e.args[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

    response_model = ProposalUserList(
        proposal_id=str(proposal_id), users=users, count=len(users)
    )
    return response_model


@router.get(
    "/proposal/{proposal_id}/principal-investigator", response_model=ProposalUser
)
async def get_proposal_principal_investigator(proposal_id: str):
    try:
        principal_investigator = await proposal_service.pi_from_proposal(proposal_id)
        if len(principal_investigator) == 0:
            # We need a PI for every proposal
            raise HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"PI not found for proposal {proposal_id}",
            )
        elif len(principal_investigator) > 1:
            # We should only have 1 PI
            raise HTTPException(
                status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Proposal {proposal_id} contains more than one PI",
            )
    except LookupError as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=e.args[0]
        )
    except Exception as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}",
        )

    response_model = ProposalUser(
        proposal_id=str(proposal_id), user=principal_investigator[0]
    )
    return response_model


@router.get("/proposal/{proposal_id}/usernames", response_model=UsernamesList)
async def get_proposal_usernames(proposal_id: str):
    try:
        # Check to see if proposal exists
        if not await proposal_service.exists(proposal_id):
            raise HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Proposal {proposal_id} not found",
            )
    except LookupError as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=e.args[0]
        )
    except Exception as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}",
        )

    proposal_usernames = await proposal_service.fetch_usernames_from_proposal(
        proposal_id
    )

    proposal_groupname = proposal_service.generate_data_session_for_proposal(
        proposal_id
    )

    response_model = UsernamesList(
        usernames=proposal_usernames,
        groupname=proposal_groupname,
        proposal_id=str(proposal_id),
        count=len(proposal_usernames),
    )
    return response_model


@router.get("/proposal/{proposal_id}/directories")
async def get_proposal_directories(proposal_id: str) -> ProposalDirectoriesList:
    try:
        directories = await proposal_service.directories(proposal_id)
        if directories is None:
            raise HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Directories not found for proposal {proposal_id}",
            )
    except LookupError as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=e.args[0]
        )
    except Exception as e:
        raise HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}",
        )

    response_model = ProposalDirectoriesList(
        directories=directories,
        directory_count=len(directories),
    )
    return response_model
