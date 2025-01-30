import datetime

from beanie import UpdateResponse
from beanie.operators import AddToSet, Set
from httpx import HTTPStatusError

from nsls2api.api.models.facility_model import FacilityName
from nsls2api.api.models.person_model import ActiveDirectoryUser
from nsls2api.models.beamlines import Beamline
from nsls2api.models.pass_models import PassCycle, PassProposalType
from nsls2api.services import (
    beamline_service,
    bnlpeople_service,
    facility_service,
    n2sn_service,
    pass_service,
    proposal_service,
)

from nsls2api.infrastructure.logging import logger
from nsls2api.models.cycles import Cycle
from nsls2api.models.jobs import JobSyncSource
from nsls2api.models.pass_models import PassProposal, PassSaf
from nsls2api.models.proposal_types import ProposalType
from nsls2api.models.proposals import Proposal, SafetyForm, User


async def worker_synchronize_dataadmins(skip_beamlines=False) -> None:
    """
    This method synchronizes the (data) admin permissions (both beamline and facility)
    for all users in the system.
    """
    start_time = datetime.datetime.now()

    facility_list = await facility_service.all_facilities()
    for facility in facility_list:
        logger.info(f"Synchronizing data admins for facility {facility.facility_id}.")
        data_admin_group_name = await facility_service.data_admin_group(
            facility.facility_id
        )
        if data_admin_group_name:
            ad_users: list[ActiveDirectoryUser] = await n2sn_service.get_users_in_group(
                data_admin_group_name
            )
            username_list = [
                u["sAMAccountName"] for u in ad_users if u["sAMAccountName"] is not None
            ]
            logger.info(f"Setting user list = {username_list} ")
            await facility_service.update_data_admins(
                facility.facility_id, username_list
            )
        else:
            logger.warning(
                f"There is no 'data_admin_group' for facility_id={facility.facility_id} defined in the database."
            )
    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Facility Data Admin permissions synchronized in {time_taken.total_seconds():,.2f} seconds"
    )

    if skip_beamlines is False:
        beamline_list: list[Beamline] = await beamline_service.all_beamlines()
        for beamline in beamline_list:
            logger.info(f"Synchronizing data admins for beamline {beamline.name}.")
            data_admin_group_name = await beamline_service.data_admin_group(
                beamline.name
            )
            ad_users: list[ActiveDirectoryUser] = await n2sn_service.get_users_in_group(
                data_admin_group_name
            )
            username_list = [
                u["sAMAccountName"] for u in ad_users if u["sAMAccountName"] is not None
            ]
            await beamline_service.update_data_admins(beamline.name, username_list)

        time_taken = datetime.datetime.now() - start_time
        logger.info(
            f"Beamline Data Admin permissions synchronized in {time_taken.total_seconds():,.2f} seconds"
        )


async def worker_synchronize_cycles_from_pass(
    facility_name: FacilityName = FacilityName.nsls2,
) -> None:
    """
    This method synchronizes the cycles for a facility from PASS.

    :param facility_name: The facility name (FacilityName).
    """
    start_time = datetime.datetime.now()

    try:
        pass_cycles: list[PassCycle] = await pass_service.get_cycles(facility_name)
    except pass_service.PassException as error:
        error_message = f"Error retrieving cycle information from PASS for {facility_name} facility."
        logger.exception(error_message)
        raise Exception(error_message) from error

    for pass_cycle in pass_cycles:
        facility = await facility_service.facility_by_pass_id(
            pass_cycle.User_Facility_ID
        )

        logger.info(f"Synchronizing cycle: {pass_cycle.Name} for {facility.name}.")

        cycle = Cycle(
            name=pass_cycle.Name,
            accepting_proposals=pass_cycle.Active,
            facility=facility.facility_id,
            year=str(pass_cycle.Year),
            start_date=pass_cycle.Start_Date,
            end_date=pass_cycle.End_Date,
            pass_description=pass_cycle.Description,
            pass_id=str(pass_cycle.ID),
        )

        updated_cycle = await Cycle.find_one(
            Cycle.name == pass_cycle.Name, Cycle.facility == facility.facility_id
        ).upsert(
            Set(
                {
                    Cycle.accepting_proposals: cycle.accepting_proposals,
                    Cycle.facility: cycle.facility,
                    Cycle.pass_description: cycle.pass_description,
                    Cycle.pass_id: cycle.pass_id,
                    Cycle.year: cycle.year,
                    Cycle.start_date: cycle.start_date,
                    Cycle.end_date: cycle.end_date,
                    Cycle.last_updated: datetime.datetime.now(),
                }
            ),
            on_insert=cycle,
            response_type=UpdateResponse.NEW_DOCUMENT,
        )

        # Now let's update the list of proposals for this cycle
        proposals_list = await pass_service.get_proposals_allocated_by_cycle(
            cycle.name, facility=facility_name
        )
        for proposal in proposals_list:
            await updated_cycle.update(
                AddToSet({Cycle.proposals: str(proposal.Proposal_ID)})
            )
            updated_cycle.last_updated = datetime.datetime.now()
            await updated_cycle.save()

    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Cycle information (for {facility.name}) synchronized in {time_taken.total_seconds():,.2f} seconds"
    )


async def worker_synchronize_proposal_types_from_pass(
    facility_name: FacilityName = FacilityName.nsls2,
) -> None:
    start_time = datetime.datetime.now()

    try:
        pass_proposal_types: list[PassProposalType] = (
            await pass_service.get_proposal_types(facility_name)
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


async def synchronize_proposal_from_pass(
    proposal_id: str, facility_name: FacilityName = FacilityName.nsls2
) -> None:
    beamline_list = []
    user_list = []
    saf_list = []

    try:
        pass_proposal: PassProposal = await pass_service.get_proposal(
            proposal_id, facility_name
        )
    except pass_service.PassException as error:
        error_message = f"Error retrieving proposal {proposal_id} from PASS"
        logger.exception(error_message)
        raise Exception(error_message) from error

    # Get the SAFs for this proposal
    pass_saf_list: list[PassSaf] = await pass_service.get_saf_from_proposal(
        proposal_id, facility_name
    )
    for saf in pass_saf_list:
        saf_beamline_list = []
        for resource in saf.Resources:
            beamline = await beamline_service.beamline_by_pass_id(str(resource.ID))
            if beamline:
                saf_beamline_list.append(beamline.name)

        saf_list.append(
            SafetyForm(
                saf_id=str(saf.SAF_ID),
                status=saf.Status,
                instruments=set(saf_beamline_list),
            )
        )

    # Get the beamlines for this proposal and add them
    for resource in pass_proposal.Resources:
        beamline = await beamline_service.beamline_by_pass_id(str(resource.ID))
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
            logger.debug(
                f"Looking up username for employee/life number = {user.BNL_ID}"
            )
            bnl_username = await bnlpeople_service.get_username_by_id(user.BNL_ID)
            logger.debug(f"     ---> {bnl_username}")
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

    # Let's add the PI explicitly anyway as PASS sometimes includes the PI in the
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

    facility = await facility_service.facility_by_pass_id(
        pass_proposal.User_Facility_ID
    )
    data_session = proposal_service.generate_data_session_for_proposal(proposal_id)

    proposal = Proposal(
        proposal_id=str(pass_proposal.Proposal_ID),
        title=pass_proposal.Title,
        data_session=data_session,
        pass_type_id=str(pass_proposal.Proposal_Type_ID),
        type=pass_proposal.Proposal_Type_Description,
        facility=facility.facility_id,
        instruments=set(beamline_list),
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
                Proposal.facility: facility.facility_id,
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


async def update_proposals_with_cycle(
    cycle_name: str, facility_name: FacilityName = FacilityName.nsls2
) -> None:
    """
    Update the cycle <-> proposals mapping for the given cycle.

    :param cycle_name: The name of the cycle to process proposals for.
    :type cycle_name: str
    """

    proposal_list = await proposal_service.fetch_proposals_for_cycle(
        cycle_name, facility_name=facility_name
    )

    logger.info(
        f"Found {len(proposal_list)} proposals for {facility_name} cycle {cycle_name}."
    )

    for proposal_id in proposal_list:
        # Add the cycle to the Proposal object

        try:
            proposal = await proposal_service.proposal_by_id(proposal_id)
            await proposal.update(AddToSet({Proposal.cycles: cycle_name}))
            proposal.last_updated = datetime.datetime.now()
            await proposal.save()
        except LookupError as error:
            logger.warning(error)


async def worker_synchronize_proposal_from_pass(
    proposal_id: str, facility: FacilityName = FacilityName.nsls2
) -> None:
    start_time = datetime.datetime.now()

    await synchronize_proposal_from_pass(proposal_id, facility)

    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Proposal {proposal_id} synchronized in {time_taken.total_seconds():,.0f} seconds"
    )


async def worker_synchronize_proposals_for_cycle_from_pass(
    cycle: str, facility_name: FacilityName = FacilityName.nsls2
) -> None:
    start_time = datetime.datetime.now()

    cycle_year = await facility_service.cycle_year(cycle, facility_name=facility_name)

    proposals = await proposal_service.fetch_proposals_for_cycle(
        cycle, facility_name=facility_name
    )
    logger.info(
        f"Synchronizing {len(proposals)} proposals for facility {facility_name} in {cycle} cycle."
    )

    for proposal_id in proposals:
        logger.info(f"Synchronizing proposal {proposal_id}.")
        await synchronize_proposal_from_pass(proposal_id, facility_name)

    commissioning_proposals: list[PassProposal] = (
        await pass_service.get_commissioning_proposals_by_year(
            cycle_year, facility_name=facility_name
        )
    )
    logger.info(
        f"Synchronizing {len(proposals)} commissioning proposals for the year {cycle_year}."
    )
    for proposal in commissioning_proposals:
        logger.info(f"Synchronizing commissioning proposal {proposal.Proposal_ID}.")
        await synchronize_proposal_from_pass(str(proposal.Proposal_ID), facility_name)

    # Now update the cycle information for each proposal
    await update_proposals_with_cycle(cycle, facility_name=facility_name)

    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Proposals for the {cycle} cycle synchronized in {time_taken.total_seconds():,.0f} seconds"
    )


async def worker_update_proposal_to_cycle_mapping(
    facility: FacilityName = FacilityName.nsls2,
    sync_source: JobSyncSource = JobSyncSource.PASS,
) -> None:
    start_time = datetime.datetime.now()

    cycles = await Cycle.find(Cycle.facility == facility).to_list()

    for individual_cycle in cycles:
        if sync_source == JobSyncSource.PASS:
            if individual_cycle:
                logger.info(
                    f"Updating proposals with information for cycle {individual_cycle.name} (from PASS)"
                )
                await update_proposals_with_cycle(individual_cycle.name)
            else:
                logger.warning(f"The cycle {individual_cycle} is not valid.")
                return

    time_taken = datetime.datetime.now() - start_time
    logger.info(
        f"Proposal/Cycle information (for {facility}) populated in {time_taken.total_seconds():,.2f} seconds"
    )
