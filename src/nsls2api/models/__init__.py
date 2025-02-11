from nsls2api.models import (
    apikeys,
    beamlines,
    cycles,
    facilities,
    jobs,
    proposal_types,
    proposals,
)

all_models = [
    facilities.Facility,
    cycles.Cycle,
    proposal_types.ProposalType,
    beamlines.Beamline,
    proposals.Proposal,
    apikeys.ApiKey,
    apikeys.ApiUser,
    jobs.BackgroundJob,
]
