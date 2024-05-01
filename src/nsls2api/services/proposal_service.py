import datetime
from pathlib import Path
from typing import Optional

from beanie import UpdateResponse
from beanie.odm.operators.find.array import ElemMatch
from beanie.operators import AddToSet, And, In, RegEx, Set, Text
from httpx import HTTPStatusError

from nsls2api.api.models.facility_model import FacilityName
from nsls2api.api.models.proposal_model import (
    ProposalDiagnostics,
    ProposalFullDetails,
)
from nsls2api.infrastructure.logging import logger
from nsls2api.models.cycles import Cycle
from nsls2api.models.jobs import JobSyncSource
from nsls2api.models.pass_models import PassProposal, PassSaf
from nsls2api.models.proposal_types import ProposalType
from nsls2api.models.proposals import Proposal, ProposalIdView, SafetyForm, User
from nsls2api.services import (
    beamline_service,
    bnlpeople_service,
    facility_service,
    pass_service,
)


async def exists(proposal_id: int) -> bool:
    proposal = await Proposal.find_one(Proposal.proposal_id == str(proposal_id))
    return False if proposal is None else True


async def proposal_count() -> int:
    return await Proposal.count()


async def recently_updated(count=5, beamline: str | None = None):
    """
    Function to fetch recently updated proposals.

    :param beamline:
    :param count: Specifies the number of recently updated proposals to fetch. Defaults to 5.
    :type count: int

    :return: List of recently updated proposals.
    :rtype: list[Proposal]

    Args:
        beamline: Optional beamline to restrict list of proposals for.
    """
    if beamline:
        # Ensure we match the case in the database for the beamline name
        beamline = beamline.upper()
        # print(f"Searching for proposals within {beamline}...")
        query = In(Proposal.instruments, [beamline])
        updated = (
            await Proposal.find_many(query)
            .sort(-Proposal.last_updated)
            .limit(count)
            .to_list()
        )
    else:
        updated = (
            await Proposal.find_many()
            .sort(-Proposal.last_updated)
            .limit(count)
            .to_list()
        )
    return updated


# async def fetch_proposals_for_cycle(cycle: str) -> list[str]:
#     proposals = await Proposal.find(In(Proposal.cycles, [cycle])).to_list()
#     result = [u.proposal_id for u in proposals if u.proposal_id is not None]
#     return result


async def fetch_proposals_for_cycle(cycle: str) -> list[str]:
    cycle = await Cycle.find_one(Cycle.name == cycle)
    if cycle is None:
        raise LookupError(f"Cycle {cycle} not found")

    # In case a 'None' has crept into the database
    if cycle.proposals is None:
        return []

    return cycle.proposals


async def fetch_data_sessions_for_username(username: str) -> list[str]:
    proposals = await Proposal.find(
        ElemMatch(Proposal.users, {"username": username})
    ).to_list()
    data_sessions = [p.data_session for p in proposals if p.data_session is not None]
    return data_sessions


def generate_data_session_for_proposal(proposal_id: int) -> str:
    return f"pass-{str(proposal_id)}"


async def proposal_by_id(proposal_id: int) -> Optional[Proposal]:
    """
    Retrieve a single proposal by its ID.

    :param proposal_id: The ID of the proposal to retrieve.
    :return: The proposal if found, or None if not found.
    """

    if not proposal_id:
        return None

    proposal: Proposal = await Proposal.find_one(
        Proposal.proposal_id == str(proposal_id)
    )

    if proposal is None:
        raise LookupError(f"Could not find a proposal with an ID of {proposal_id}")

    return proposal


# Get a list of proposals that match the search criteria
async def search_proposals(search_text: str) -> Optional[list[Proposal]]:
    query = Text(search=search_text, case_sensitive=False)

    if len(search_text) < 3:
        return []

    logger.debug(f"Searching for '{search_text}'")

    # Not sure we need to sort here - but hey why not!
    found_proposals = (
        await Proposal.find(query).sort([("score", {"$meta": "textScore"})]).to_list()
    )

    logger.info(
        f"Found {len(found_proposals)} proposals by search for the text '{search_text}'"
    )

    # Now do a special search just for the proposal id
    found_proposals += await Proposal.find(
        RegEx(Proposal.proposal_id, pattern=f"{search_text}")
    ).to_list()

    logger.info(
        f"Found {len(found_proposals)} proposals  after searching for '{search_text}' in just the proposal_id field"
    )

    return found_proposals


# Get a list of proposals that match the given criteria
async def fetch_proposals(
    proposal_id: list[str] | None = None,
    beamline: list[str] | None = None,
    cycle: list[str] | None = None,
    facility: list[str] | None = None,
    page_size: int = 10,
    page: int = 1,
    include_directories: bool = False,
) -> Optional[list[ProposalFullDetails]]:
    query = []

    if beamline:
        query.append(In(Proposal.instruments, beamline))

    if cycle:
        query.append(In(Proposal.cycles, cycle))

    if proposal_id:
        query.append(In(Proposal.proposal_id, proposal_id))

    if len(query) == 0:
        proposals = (
            await Proposal.find_many()
            .sort(-Proposal.last_updated)
            .limit(page_size)
            .skip(page_size * (page - 1))
            .to_list()
        )
    else:
        proposals = (
            await Proposal.find_many(And(*query))
            .sort(-Proposal.last_updated)
            .limit(page_size)
            .skip(page_size * (page - 1))
            .to_list()
        )

    # Add directories field to each proposal
    if include_directories:
        detailed_proposals = []
        for proposal in proposals:
            new_proposal = ProposalFullDetails(
                **proposal.model_dump(),
                directories=await directories(proposal.proposal_id),
            )
            detailed_proposals.append(new_proposal)
        return detailed_proposals
    else:
        return proposals


async def proposal_type_description_from_pass_type_id(
    pass_type_id: int,
) -> Optional[str]:
    proposal_type = await ProposalType.find_one(
        ProposalType.pass_id == str(pass_type_id)
    )
    if proposal_type is None:
        error_message = f"PASS Proposal type {pass_type_id} not found.  Check that the proposal types have been synchronized."
        logger.error(error_message)
        raise LookupError(error_message)
    else:
        return proposal_type.description


async def data_session_for_proposal(proposal_id: int) -> Optional[str]:
    proposal = await Proposal.find_one(Proposal.proposal_id == str(proposal_id))
    return proposal.data_session


async def beamlines_for_proposal(proposal_id: int) -> Optional[list[str]]:
    proposal = await proposal_by_id(proposal_id)
    return proposal.instruments


async def cycles_for_proposal(proposal_id: int) -> Optional[list[str]]:
    proposal = await proposal_by_id(proposal_id)
    return proposal.cycles


async def fetch_users_on_proposal(proposal_id: int) -> Optional[list[User]]:
    """
    Fetches the users associated with a given proposal.

    Args:
        proposal_id (int): The ID of the proposal.

    Returns:
        Optional[list[User]]: A list of User objects associated with the proposal, or None if the proposal is not found.
    """
    proposal = await proposal_by_id(proposal_id)
    return proposal.users


async def fetch_usernames_from_proposal(
    proposal_id: int,
) -> Optional[list[str]]:
    proposal = await proposal_by_id(proposal_id)

    if proposal is None:
        raise LookupError(f"Proposal {proposal_id} not found")

    usernames = [u.username for u in proposal.users if u.username is not None]
    return usernames


async def pi_from_proposal(proposal_id: int) -> Optional[list[User]]:
    proposal = await proposal_by_id(proposal_id)

    pi = [u for u in proposal.users if u.is_pi]

    if len(pi) == 0:
        raise LookupError(f"Proposal {proposal_id} does not contain any PIs.")
    elif len(pi) > 1:
        raise LookupError(f"Proposal {proposal_id} contains {len(pi)} different PIs.")
    else:
        return pi


# TODO: There seems to be a data integrity issue that not all commissioning proposals have a beamline listed.
async def commissioning_proposals(beamline: str | None = None):
    if beamline:
        # Ensure we match the case in the database for the beamline name
        beamline = beamline.upper()

        proposals = Proposal.find(In(Proposal.instruments, [beamline])).find(
            Proposal.pass_type_id == "300005"
        )
    else:
        proposals = Proposal.find(
            Proposal.pass_type_id == "300005", projection_model=ProposalIdView
        )

    commissioning_proposal_list = [
        p.proposal_id for p in await proposals.to_list() if p.proposal_id is not None
    ]

    return commissioning_proposal_list


async def has_valid_cycle(proposal: Proposal):
    # If we don't have any cycles listed and this is not a commissioning
    # proposal then the cycle information is invalid
    return not (
        (len(proposal.cycles) == 0)
        and (
            proposal.pass_type_id != 300005
            or proposal.type == "Beamline Commissioning (beamline staff only)"
        )
    )


async def is_commissioning(proposal: Proposal):
    return (
        proposal.pass_type_id == "300005"
        or proposal.type == "Beamline Commissioning (beamline staff only)"
    )


# Return the directories and permissions that should be present for a given proposal
async def directories(proposal_id: int):
    proposal = await proposal_by_id(proposal_id)

    # if any of the following are null or zero length, then we don't have
    # enough information to create any directories
    error_msg = []

    if proposal.data_session is None:
        error_text = (
            f"Proposal {str(proposal.proposal_id)} does not contain a data_session."
        )
        logger.error(error_text)
        error_msg.append(error_text)

    if not await has_valid_cycle(proposal) and not await is_commissioning(proposal):
        error_text = f"Proposal {str(proposal.proposal_id)} does not contain any cycle information."
        logger.error(error_text)
        error_msg.append(error_text)

    if len(proposal.instruments) == 0:
        error_text = (
            f"Proposal {str(proposal.proposal_id)} does not contain any beamlines."
        )
        logger.error(error_text)
        error_msg.append(error_text)

    if len(error_msg) > 0:
        raise Exception(error_msg)

    directory_list = []

    for beamline in proposal.instruments:
        data_root = Path(await beamline_service.data_root_directory(beamline))
        # print(f"Data Root ({beamline}) = {data_root}")

        service_accounts = await beamline_service.service_accounts(beamline)
        # print(f"service_accounts: {service_accounts}")

        if await is_commissioning(proposal):
            cycles = ["commissioning"]
        else:
            cycles = proposal.cycles

        for cycle in cycles:
            beamline_tla = str(beamline).lower()

            users_acl: list[dict[str, str]] = []
            groups_acl: list[dict[str, str]] = []

            users_acl.append({"nsls2data": "rw"})
            users_acl.append({f"{service_accounts.workflow}": "rw"})
            users_acl.append({f"{service_accounts.ioc}": "rw"})

            # If beamline uses SynchWeb then add access for synchweb user
            if beamline_service.uses_synchweb(beamline_tla):
                users_acl.append({"synchweb": "r"})

            groups_acl.append({str(proposal.data_session): "rw"})

            # Add LSDC beamline users for the appropriate beamlines (i.e. if the account is defined)
            if service_accounts.lsdc:
                users_acl.append({f"{service_accounts.lsdc}": "rw"})

            groups_acl.append({"n2sn-right-dataadmin": "rw"})
            groups_acl.append(
                {
                    f"{await beamline_service.custom_data_admin_group(beamline_tla)}": "rw"
                }
            )

            directory = {
                "path": str(
                    data_root / "proposals" / str(cycle) / proposal.data_session
                ),
                "beamline": beamline.upper(),
                "cycle": str(cycle),
                "owner": "nsls2data",
                "group": proposal.data_session,
                "users": users_acl,
                "groups": groups_acl,
            }
            directory_list.append(directory)

    return directory_list


async def diagnostic_details_by_id(proposal_id: str) -> Optional[ProposalDiagnostics]:
    proposal = await proposal_by_id(proposal_id)

    if proposal is None:
        raise LookupError(f"Proposal {proposal_id} not found")

    pi = await pi_from_proposal(proposal.proposal_id)

    proposal_diagnostics = ProposalDiagnostics(
        proposal_id=proposal.proposal_id,
        title=proposal.title,
        proposal_type=proposal.type,
        pi=pi[0],
        users=proposal.users,
        data_session=proposal.data_session,
        beamlines=proposal.instruments,
        cycles=proposal.cycles,
        updated=proposal.last_updated,
    )

    return proposal_diagnostics


async def worker_synchronize_proposal_types_from_pass(
    facility_name: FacilityName = FacilityName.nsls2,
) -> None:
    start_time = datetime.datetime.now()

    try:
        pass_proposal_types: PassProposal = await pass_service.get_proposal_types(
            facility_name
        )
    except pass_service.PassException as error:
        error_message = (
            f"Error retrieving proposal types from PASS for {facility_name} facility."
        )
        logger.exception(error_message)
        raise Exception(error_message) from error

    for pass_proposal_type in pass_proposal_types:
        facility = await facility_service.facility_by_pass_id(
            pass_proposal_type.User_Facility_ID
        )

        proposal_type = ProposalType(
            code=pass_proposal_type.Code,
            facility_id=facility.facility_id,
            pass_id=str(pass_proposal_type.ID),
            description=pass_proposal_type.Description,
            pass_description=pass_proposal_type.Description,
        )

        response = await ProposalType.find_one(
            ProposalType.pass_id == str(pass_proposal_type.ID)
        ).upsert(
            Set(
                {
                    ProposalType.code: pass_proposal_type.Code,
                    ProposalType.pass_description: pass_proposal_type.Description,
                    ProposalType.description: pass_proposal_type.Description,
                    ProposalType.facility_id: facility.facility_id,
                    ProposalType.last_updated: datetime.datetime.now(),
                }
            ),
            on_insert=proposal_type,
            response_type=UpdateResponse.UPDATE_RESULT,
        )

    time_taken = datetime.datetime.now() - start_time
    logger.debug(f"Response: {response}")
    logger.info(
        f"Proposal type information (for {facility.name}) synchronized in {time_taken.total_seconds():,.2f} seconds"
    )


async def synchronize_proposal_from_pass(proposal_id: int) -> None:
    beamline_list = []
    user_list = []
    saf_list = []

    try:
        pass_proposal: PassProposal = await pass_service.get_proposal(proposal_id)
    except pass_service.PassException as error:
        error_message = f"Error retrieving proposal {proposal_id} from PASS"
        logger.exception(error_message)
        raise Exception(error_message) from error

    # Get the SAFs for this proposal
    pass_saf_list: list[PassSaf] = await pass_service.get_saf_from_proposal(proposal_id)
    for saf in pass_saf_list:
        saf_beamline_list = []
        for resource in saf.Resources:
            beamline = await beamline_service.beamline_by_pass_id(resource.ID)
            if beamline:
                saf_beamline_list.append(beamline.name)

        saf_list.append(
            SafetyForm(
                saf_id=str(saf.SAF_ID), status=saf.Status, instruments=saf_beamline_list
            )
        )

    # Get the beamlines for this proposal and add them
    for resource in pass_proposal.Resources:
        beamline = await beamline_service.beamline_by_pass_id(resource.ID)
        if beamline:
            beamline_list.append(beamline.name)

    pi_found_in_experimenters = False

    # Get the users for this proposal
    for user in pass_proposal.Experimenters:
        user_is_pi = False
        bnl_username = None

        if pass_proposal.PI is None:
            logger.warning(f"Proposal {proposal_id} does not have a PI.")
            continue
        else:
            if str(pass_proposal.PI.BNL_ID).casefold() == str(user.BNL_ID).casefold():
                user_is_pi = True
                pi_found_in_experimenters = True
        try:
            bnl_username = await bnlpeople_service.get_username_by_id(user.BNL_ID)
        except HTTPStatusError as error:
            logger.error(f"Could not find BNL username for BNL ID '{user.BNL_ID}'.")
            logger.error(f"BNL People API returned: {error}")
            bnl_username = None

        userinfo = User(
            first_name=user.First_Name,
            last_name=user.Last_Name,
            email=user.Email,
            bnl_id=user.BNL_ID,
            username=bnl_username,
            is_pi=user_is_pi,
        )
        user_list.append(userinfo)

    # Let's add the PI explictly anyway as PASS sometimes includes the PI in the
    # Experimenters list and sometimes not.
    if pass_proposal.PI and not pi_found_in_experimenters:
        bnl_username = await bnlpeople_service.get_username_by_id(
            pass_proposal.PI.BNL_ID
        )
        pi_info = User(
            first_name=pass_proposal.PI.First_Name,
            last_name=pass_proposal.PI.Last_Name,
            email=pass_proposal.PI.Email,
            bnl_id=pass_proposal.PI.BNL_ID,
            username=bnl_username,
            is_pi=True,
        )
        user_list.append(pi_info)

    data_session = generate_data_session_for_proposal(proposal_id)

    proposal = Proposal(
        proposal_id=str(pass_proposal.Proposal_ID),
        title=pass_proposal.Title,
        data_session=data_session,
        pass_type_id=str(pass_proposal.Proposal_Type_ID),
        type=pass_proposal.Proposal_Type_Description,
        instruments=beamline_list,
        safs=saf_list,
        users=user_list,
        last_updated=datetime.datetime.now(),
    )

    response = await Proposal.find_one(Proposal.proposal_id == str(proposal_id)).upsert(
        Set(
            {
                Proposal.title: pass_proposal.Title,
                Proposal.data_session: data_session,
                Proposal.pass_type_id: str(pass_proposal.Proposal_Type_ID),
                Proposal.type: pass_proposal.Proposal_Type_Description,
                Proposal.instruments: beamline_list,
                Proposal.safs: saf_list,
                Proposal.users: user_list,
                Proposal.last_updated: datetime.datetime.now(),
            }
        ),
        on_insert=proposal,
        response_type=UpdateResponse.UPDATE_RESULT,
    )
    logger.debug(f"Response: {response}")


async def worker_synchronize_proposal_from_pass(proposal_id: int) -> None:
    start_time = datetime.datetime.now()

    await synchronize_proposal_from_pass(proposal_id)

    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Proposal {proposal_id} synchronized in {time_taken.total_seconds():,.0f} seconds"
    )


async def worker_synchronize_proposals_for_cycle_from_pass(cycle: str) -> None:
    start_time = datetime.datetime.now()

    proposals = await fetch_proposals_for_cycle(cycle)
    logger.info(f"Synchronizing {len(proposals)} proposals for {cycle} cycle.")

    for proposal_id in proposals:
        logger.info(f"Synchronizing proposal {proposal_id}.")
        await synchronize_proposal_from_pass(proposal_id)

    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Proposals for the {cycle} cycle synchronized in {time_taken.total_seconds():,.0f} seconds"
    )


async def update_proposals_with_cycle_information_from_pass(cycle: Cycle) -> None:
    """
    Update all proposals with the given cycle information.

    :param cycle: The cycle information to update the proposals with.
    :type cycle: Cycle
    """

    allocations = await pass_service.get_proposals_allocated_by_cycle(cycle.name)

    for allocation in allocations:
        # Add the proposal to the Cycle object

        # logger.info(f"Going to add proposal {proposal_id} to cycle {cycle.name}")

        await cycle.update(AddToSet({Cycle.proposals: str(allocation.Proposal_ID)}))
        cycle.last_updated = datetime.datetime.now()
        await cycle.save()

        try:
            proposal = await proposal_by_id(allocation.Proposal_ID)
            await proposal.update(AddToSet({Proposal.cycles: cycle.name}))
            proposal.last_updated = datetime.datetime.now()
            await proposal.save()
        except LookupError as error:
            logger.warning(error)


async def worker_update_cycle_information(
    facility: FacilityName = FacilityName.nsls2,
    cycle: Optional[str] = None,
    sync_source: JobSyncSource = JobSyncSource.PASS,
) -> None:
    start_time = datetime.datetime.now()

    # TODO: Add test that cycle and facility combination is valid

    if cycle:
        # If we've specified a cycle then only sync that one
        cycles = await Cycle.find(
            Cycle.name == str(cycle), Cycle.facility == facility
        ).to_list()
    else:
        cycles = await Cycle.find(Cycle.facility == facility).to_list()

    for individual_cycle in cycles:
        if sync_source == JobSyncSource.PASS:
            logger.info(
                f"Updating proposals with information for cycle {individual_cycle.name} (from PASS)"
            )
            await update_proposals_with_cycle_information_from_pass(individual_cycle)

    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Proposal/Cycle information (for {facility}) populated in {time_taken.total_seconds():,.2f} seconds"
    )
