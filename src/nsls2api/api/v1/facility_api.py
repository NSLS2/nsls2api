import fastapi

from nsls2api.api.models.facility_model import (
    FacilityCurrentOperatingCycleResponseModel,
    FacilityCyclesResponseModel,
    FacilityName,
)
from nsls2api.api.models.proposal_model import CycleProposalList
from nsls2api.services import facility_service, proposal_service

router = fastapi.APIRouter()


# TODO: Add back into schema when implemented.
@router.get(
    "/facility/{facility}/cycles/current",
    response_model=FacilityCurrentOperatingCycleResponseModel,
    include_in_schema=True,
)
async def get_current_operating_cycle(facility: FacilityName):
    current_cycle = await facility_service.current_operating_cycle(facility.name)
    if current_cycle is None:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No current operating cycle was found for facility {facility.name}"
            },
            status_code=404,
        )

    # TODO: Maybe add a health check here
    # print("Are we healthy ? ")
    # print(await facility_service.is_healthy(facility.name))

    response_model = FacilityCurrentOperatingCycleResponseModel(
        facility=facility.name, cycle=current_cycle
    )

    return response_model


@router.get(
    "/facility/{facility}/cycles",
    response_model=FacilityCyclesResponseModel,
    include_in_schema=True,
)
async def get_facility_cycles(facility: FacilityName):
    cycle_list = await facility_service.facility_cycles(facility.name)
    if cycle_list is None:
        return fastapi.responses.JSONResponse(
            {"error": f"No cycles were found for facility {facility.name}"},
            status_code=404,
        )
    response_model = FacilityCyclesResponseModel(
        facility=facility.name, cycles=cycle_list
    )
    return response_model


@router.get(
    "/facility/{facility}/cycle/{cycle}/proposals",
    response_model=CycleProposalList,
    include_in_schema=True,
)
async def get_proposals_for_cycle(facility: FacilityName, cycle: str):
    proposal_list = await proposal_service.fetch_proposals_for_cycle(cycle, facility)
    if proposal_list is None:
        return fastapi.responses.JSONResponse(
            {
                "error": f"No proposals were found for cycle {cycle} for facility {facility.name}"
            },
            status_code=404,
        )
    model = CycleProposalList(
        cycle=cycle, proposals=proposal_list, count=len(proposal_list)
    )
    return model
