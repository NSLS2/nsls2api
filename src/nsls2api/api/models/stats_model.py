from typing import Optional

import pydantic


class ProposalsPerCycleModel(pydantic.BaseModel):
    cycle: str
    proposal_count: int = 0


class StatsModel(pydantic.BaseModel):
    facility_count: int
    proposal_count: int
    beamline_count: int
    commissioning_proposal_count: int
    nsls2_data_health: bool
    lbms_data_health: bool
    nsls2_proposals_per_cycle: Optional[list[ProposalsPerCycleModel]]
    lbms_proposals_per_cycle: Optional[list[ProposalsPerCycleModel]]


class AboutModel(pydantic.BaseModel):
    description: str
    version: str
