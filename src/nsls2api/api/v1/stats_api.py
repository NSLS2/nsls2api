import fastapi

from nsls2api._version import version as api_version
from nsls2api.infrastructure.logging import logger
from nsls2api.api.models.facility_model import FacilityName
from nsls2api.api.models.stats_model import (
    AboutModel,
    ProposalsPerCycleModel,
    StatsModel,
)
from nsls2api.infrastructure.container_utils import get_container_info
from nsls2api.services import (
    beamline_service,
    facility_service,
    proposal_service,
)

router = fastapi.APIRouter()


@router.get("/stats", response_model=StatsModel)
async def stats():
    total_proposals = await proposal_service.proposal_count()
    beamlines = await beamline_service.beamline_count()
    facilities = await facility_service.facilities_count()
    commissioning_proposals = await proposal_service.commissioning_proposals()

    nsls2_data_health = await facility_service.is_healthy("nsls2")

    # Get the NSLS-II proposals per cycle
    nsls2_proposals_per_cycle: list[ProposalsPerCycleModel] = []
    nsls2_cycle_list = await facility_service.facility_cycles("nsls2")
    for cycle in nsls2_cycle_list:
        try:
            # Fetch proposals for the cycle
            proposal_list = await proposal_service.fetch_proposals_for_cycle(cycle)
            if proposal_list is not None:
                # Create a model for the cycle and proposal count
                model = ProposalsPerCycleModel(cycle=cycle, proposal_count=len(proposal_list))
                nsls2_proposals_per_cycle.append(model)
        except LookupError as e:
            # Handle the case where the cycle is not found
            logger.error(f"Cycle {cycle} not found for NSLS-II facility.")
            continue

    lbms_data_health = await facility_service.is_healthy("lbms")
    # Get the LBMS proposals per cycle
    lbms_proposals_per_cycle: list[ProposalsPerCycleModel] = []
    lbms_cycle_list = await facility_service.facility_cycles("lbms")
    for cycle in lbms_cycle_list:
        try:
            proposal_list = await proposal_service.fetch_proposals_for_cycle(cycle, facility_name=FacilityName.lbms)
            if proposal_list is not None:
                model = ProposalsPerCycleModel(cycle=cycle, proposal_count=len(proposal_list))
                lbms_proposals_per_cycle.append(model)
        except LookupError as e:
            # Handle the case where the cycle is not found
            logger.error(f"Cycle {cycle} not found for LBMS facility.")
            continue

    model = StatsModel(
        facility_count=facilities,
        beamline_count=beamlines,
        proposal_count=total_proposals,
        commissioning_proposal_count=commissioning_proposals.count,
        nsls2_data_health=nsls2_data_health,
        lbms_data_health=lbms_data_health,
        nsls2_proposals_per_cycle=nsls2_proposals_per_cycle,
        lbms_proposals_per_cycle=lbms_proposals_per_cycle,
    )
    return model

@router.get("/about", response_model=AboutModel)
async def about():
    container_info = get_container_info()
    model = AboutModel(
        version=api_version, 
        description="NSLS-II Facility API",
        container_info=container_info
    )
    return model
