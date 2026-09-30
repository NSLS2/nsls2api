
from nsls2api.api.models.person_model import BNLPerson
from nsls2api.infrastructure.logging import logger
from nsls2api.services.helpers import (
    _call_async_webservice_with_client,
    httpx_client_wrapper,
)

base_url = "https://api.bnl.gov/BNLPeople"


class AmbiguousPersonLookupError(Exception):
    """Raised when a person lookup returns multiple results (data integrity issue).

    ``AmbiguousPersonLookupError`` does not derive from ``LookupError``.
    ``LookupError`` represents an expected condition and is generally converted
    into a 404 NOT FOUND response. An ambiguous result indicates a data
    integrity issue with the upstream service and should generally propagate
    to the global exception handler as a 500 INTERNAL SERVER ERROR or
    502 BAD GATEWAY response.
    """

    pass


async def _call_bnlpeople_webservice(url: str):
    return await _call_async_webservice_with_client(url, client=httpx_client_wrapper())


async def get_all_people():
    url = f"{base_url}/api/BNLPeople"
    people = await _call_bnlpeople_webservice(url)
    return people


async def get_person_by_username(username: str) -> BNLPerson:
    url = f"{base_url}/api/BNLPeople?accountName={username}"
    person = await _call_bnlpeople_webservice(url)
    if len(person) == 0:
        logger.warning(
            f"BNL People API could not find a person with a username of '{username}'"
        )
        raise LookupError(f"BNL People API could not find a person with a username of '{username}'")
    if len(person) > 1:
        logger.error(
            f"BNL People API returned {len(person)} people for username '{username}' - ambiguous result"
        )
        raise AmbiguousPersonLookupError(
            f"BNL People API returned {len(person)} people for username '{username}' - ambiguous result"
        )
    return BNLPerson(**person[0])


async def get_username_by_id(lifenumber: str | None) -> str | None:
    if lifenumber is None:
        return None

    url = f"{base_url}/api/BNLPeople?employeeNumber={lifenumber}"
    logger.debug(f"Calling URL: {url}")

    try:
        person = await _call_bnlpeople_webservice(url)
    except Exception:
        logger.exception(
            f"BNL People API query failed for lifenumber {lifenumber}"
        )
        return None

    if len(person) == 0:
        logger.warning(
            f"BNL People API could not find a person with an employee/life number of '{lifenumber}'"
        )
        raise LookupError(
            f"BNL People API could not find a person with an employee/life number of '{lifenumber}'"
        )

    if len(person) > 1:
        logger.error(
            f"BNL People API returned {len(person)} people for employee/life number '{lifenumber}' - ambiguous result"
        )
        raise AmbiguousPersonLookupError(
            f"BNL People API returned {len(person)} people for employee/life number '{lifenumber}' - ambiguous result"
        )

    bnl_person = BNLPerson(**person[0])

    # Guard against the BNLPeople API giving us an empty string.
    if len(bnl_person.ActiveDirectoryName) > 0:
        return bnl_person.ActiveDirectoryName

    return None


async def get_person_by_id(lifenumber: str) -> BNLPerson | None:
    if lifenumber is None:
        return None

    url = f"{base_url}/api/BNLPeople?employeeNumber={lifenumber}"
    logger.debug(f"Calling URL: {url}")

    try:
        person = await _call_bnlpeople_webservice(url)
    except Exception:
        logger.exception(
            f"BNL People API query failed for lifenumber {lifenumber}"
        )
        return None

    if len(person) == 0:
        logger.warning(
            f"BNL People API could not find a person with an employee/life number of '{lifenumber}'"
        )
        raise LookupError(
            f"BNL People API could not find a person with an employee/life number of '{lifenumber}'"
        )

    if len(person) > 1:
        logger.error(
            f"BNL People API returned {len(person)} people for employee/life number "
            f"'{lifenumber}' - ambiguous result"
        )
        raise AmbiguousPersonLookupError(
            f"BNL People API returned {len(person)} people for employee/life number "
            f"'{lifenumber}' - ambiguous result"
        )

    return BNLPerson(**person[0])


async def get_person_by_email(email: str) -> BNLPerson:
    url = f"{base_url}/api/BNLPeople?email={email}"
    person = await _call_bnlpeople_webservice(url)
    if len(person) == 0:
        logger.warning(
            f"BNL People API could not find a person with an email of '{email}'"
        )
        raise LookupError(f"BNL People API could not find a person with an email of '{email}'")
    if len(person) > 1:
        logger.error(
            f"BNL People API returned {len(person)} people for email '{email}' - ambiguous result"
        )
        raise AmbiguousPersonLookupError(
            f"BNL People API returned {len(person)} people for email '{email}' - ambiguous result"
        )
    return BNLPerson(**person[0])


async def get_people_by_department(
    department_code: str,
) -> list[BNLPerson] | None:
    url = f"{base_url}/api/BNLPeople?departmentCode={department_code}"
    people = await _call_bnlpeople_webservice(url)
    if len(people) == 0:
        raise LookupError(
            f"BNL People API could not find a person with the department code of '{department_code}'"
        )
    people_in_department = [BNLPerson(**p) for p in people]
    return people_in_department


async def get_people_by_status(status: str):
    if status.title() not in ("Active", "Inactive", "Pending"):
        raise ValueError("Status must be either 'Active', 'Inactive', 'Pending'")
    url = f"{base_url}/api/BNLPeople?status={status}"
    people = await _call_bnlpeople_webservice(url)
    return people


async def get_people_by_calcstatus(calculated_status: str):
    if calculated_status.title() not in ("Active", "Inactive"):
        raise ValueError("Calculated Status must be either 'Active', 'Inactive'")
    url = f"{base_url}/api/BNLPeople?status={calculated_status}"
    people = await _call_bnlpeople_webservice(url)
    return people
