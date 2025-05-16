import fastapi
from fastapi import Depends

from nsls2api.api.models.facility_model import (
    FacilityCurrentOperatingCycleResponseModel,
    FacilityCyclesResponseModel,
    FacilityName,
)
from nsls2api.api.models.proposal_model import CycleProposalList
from nsls2api.infrastructure.logging import logger
from nsls2api.infrastructure.security import validate_admin_role
from nsls2api.services import facility_service, proposal_service
from nsls2api.services.facility_service import (
    CycleNotFoundError,
    CycleOperationError,
    CycleUpdateError,
    CycleVerificationError,
)

router = fastapi.APIRouter()


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


@router.post(
    "/facility/{facility}/cycles/current",
    response_model=FacilityCurrentOperatingCycleResponseModel,
    dependencies=[Depends(validate_admin_role)],
)
async def set_current_operating_cycle(
    facility: FacilityName,
    cycle: str,
):
    try:
        await facility_service.set_current_operating_cycle(facility, cycle)
    except CycleNotFoundError:
        # The requested cycle does not exist
        error_message = f"Cycle {cycle} not found for facility {facility.name}"
        logger.error(error_message)
        return fastapi.responses.JSONResponse(
            {"error": error_message}, status_code=fastapi.status.HTTP_400_BAD_REQUEST
        )
    except CycleVerificationError:
        # The verification of the cycle failed
        error_message = (
            f"Cycle {cycle} verification failed for facility {facility.name}"
        )
        logger.error(error_message)
        return fastapi.responses.JSONResponse(
            {"error": error_message}, status_code=fastapi.status.HTTP_400_BAD_REQUEST
        )
    except CycleUpdateError as e:
        # Handle update failure with access to the reason
        logger.error(f"Update failed: {e.reason}")
        return fastapi.responses.JSONResponse(
            {"error": "Cycle Update failed"},
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
        )
    except CycleOperationError:
        # Catch-all for any other errors that may occur
        logger.error("Cycle Update failed")
        return fastapi.responses.JSONResponse(
            {"error": "Cycle Update failed"},
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response_model = FacilityCurrentOperatingCycleResponseModel(
        facility=facility.name, cycle=cycle
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
