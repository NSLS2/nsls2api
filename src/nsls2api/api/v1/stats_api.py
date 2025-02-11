import fastapi

from nsls2api._version import version as api_version
from nsls2api.api.models.stats_model import (
    AboutModel,
    ProposalsPerCycleModel,
    StatsModel,
)
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
    commissioning = len(await proposal_service.commissioning_proposals())

    nsls2_data_health = await facility_service.is_healthy("nsls2")

    # Get the NSLS-II proposals per cycle
    nsls2_proposals_per_cycle: list[ProposalsPerCycleModel] = []
    nsls2_cycle_list = await facility_service.facility_cycles("nsls2")
    for cycle in nsls2_cycle_list:
        proposal_list = await proposal_service.fetch_proposals_for_cycle(cycle)
        if proposal_list is not None:
            model = ProposalsPerCycleModel(
                cycle=cycle, proposal_count=len(proposal_list)
            )
            nsls2_proposals_per_cycle.append(model)

    lbms_data_health = await facility_service.is_healthy("lbms")

    # Get the LBMS proposals per cycle
    lbms_proposals_per_cycle: list[ProposalsPerCycleModel] = []
    lbms_cycle_list = await facility_service.facility_cycles("lbms")
    for cycle in lbms_cycle_list:
        proposal_list = await proposal_service.fetch_proposals_for_cycle(cycle)
        if proposal_list is not None:
            model = ProposalsPerCycleModel(
                cycle=cycle, proposal_count=len(proposal_list)
            )
            lbms_proposals_per_cycle.append(model)

    model = StatsModel(
        facility_count=facilities,
        beamline_count=beamlines,
        proposal_count=total_proposals,
        commissioning_proposal_count=commissioning,
        nsls2_data_health=nsls2_data_health,
        lbms_data_health=lbms_data_health,
        nsls2_proposals_per_cycle=nsls2_proposals_per_cycle,
        lbms_proposals_per_cycle=lbms_proposals_per_cycle,
    )
    return model


@router.get("/about", response_model=AboutModel)
async def about():
    model = AboutModel(version=api_version, description="NSLS-II Facility API")
    return model
