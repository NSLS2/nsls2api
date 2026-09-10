from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from nsls2api.main import app


@pytest.mark.anyio
async def test_get_person_by_username_not_found():
    """Test that requesting a non-existent username returns 404."""
    with patch(
        "nsls2api.services.bnlpeople_service._call_bnlpeople_webservice",
        new_callable=AsyncMock,
        return_value=[],
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/v1/person/username/nonexistent_user_xyz123")
    
    assert response.status_code == 404
    response_json = response.json()
    assert "detail" in response_json
    assert "nonexistent_user_xyz123" in response_json["detail"]
    assert "not found" in response_json["detail"].lower()


@pytest.mark.anyio
async def test_get_person_by_username_multiple_found():
    """Test that multiple people with same username returns 500 via exception handler."""
    # Mock API response with 2 people
    mock_api_response = [
        {
            "FirstName": "John",
            "LastName": "Doe",
            "BNLEmail": "john.doe@bnl.gov",
            "EmployeeNumber": "123456",
            "Institution": "Brookhaven National Laboratory",
            "ActiveDirectoryName": "jdoe",
            "CyberAgreementSigned": None,
            "EmployeeStatus": "Active",
            "EmployeeType": "Employee",
            "FacilityCode": None,
            "Facility": None,
        },
        {
            "FirstName": "John",
            "LastName": "Doe",
            "BNLEmail": "john.doe@bnl.gov",
            "EmployeeNumber": "789012",
            "Institution": "Brookhaven National Laboratory",
            "ActiveDirectoryName": "jdoe",
            "CyberAgreementSigned": None,
            "EmployeeStatus": "Active",
            "EmployeeType": "Employee",
            "FacilityCode": None,
            "Facility": None,
        },
    ]
    
    with patch(
        "nsls2api.services.bnlpeople_service._call_bnlpeople_webservice",
        new_callable=AsyncMock,
        return_value=mock_api_response,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/v1/person/username/jdoe")
    
    assert response.status_code == 500


@pytest.mark.anyio
async def test_get_person_by_username_success():
    """Test that valid username returns 200 with person data."""
    mock_api_response = [
        {
            "FirstName": "John",
            "LastName": "Doe",
            "BNLEmail": "john.doe@bnl.gov",
            "EmployeeNumber": "123456",
            "Institution": "Brookhaven National Laboratory",
            "ActiveDirectoryName": "jdoe",
            "CyberAgreementSigned": None,
            "EmployeeStatus": "Active",
            "EmployeeType": "Employee",
            "FacilityCode": None,
            "Facility": None,
        }
    ]
    
    with patch(
        "nsls2api.services.bnlpeople_service._call_bnlpeople_webservice",
        new_callable=AsyncMock,
        return_value=mock_api_response,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/v1/person/username/jdoe")
    
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["firstname"] == "John"
    assert response_json["lastname"] == "Doe"
    assert response_json["email"] == "john.doe@bnl.gov"
    assert response_json["username"] == "jdoe"
    assert response_json["bnl_employee"] is True


# ============================================================================
# EMAIL TESTS
# ============================================================================


@pytest.mark.anyio
async def test_get_person_by_email_not_found():
    """Test that requesting a non-existent email returns 404."""
    with patch(
        "nsls2api.services.bnlpeople_service._call_bnlpeople_webservice",
        new_callable=AsyncMock,
        return_value=[],
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/v1/person/email/nonexistent@example.com")
    
    assert response.status_code == 404
    response_json = response.json()
    assert "detail" in response_json
    assert "nonexistent@example.com" in response_json["detail"]
    assert "not found" in response_json["detail"].lower()


@pytest.mark.anyio
async def test_get_person_by_email_multiple_found():
    """Test that multiple people with same email returns 500 via exception handler."""
    # Mock API response with 2 people
    mock_api_response = [
        {
            "FirstName": "Jane",
            "LastName": "Smith",
            "BNLEmail": "jane@example.com",
            "EmployeeNumber": "123456",
            "Institution": "Brookhaven National Laboratory",
            "ActiveDirectoryName": "jsmith",
            "CyberAgreementSigned": None,
            "EmployeeStatus": "Active",
            "EmployeeType": "Employee",
            "FacilityCode": None,
            "Facility": None,
        },
        {
            "FirstName": "Jane",
            "LastName": "Smith",
            "BNLEmail": "jane@example.com",
            "EmployeeNumber": "654321",
            "Institution": "Brookhaven National Laboratory",
            "ActiveDirectoryName": "jsmith2",
            "CyberAgreementSigned": None,
            "EmployeeStatus": "Active",
            "EmployeeType": "Employee",
            "FacilityCode": None,
            "Facility": None,
        },
    ]
    
    with patch(
        "nsls2api.services.bnlpeople_service._call_bnlpeople_webservice",
        new_callable=AsyncMock,
        return_value=mock_api_response,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/v1/person/email/jane@example.com")
    
    assert response.status_code == 500


@pytest.mark.anyio
async def test_get_person_by_email_success():
    """Test that valid email returns 200 with person data."""
    mock_api_response = [
        {
            "FirstName": "Jane",
            "LastName": "Smith",
            "BNLEmail": "jane.smith@bnl.gov",
            "EmployeeNumber": "654321",
            "Institution": "Brookhaven National Laboratory",
            "ActiveDirectoryName": "jsmith",
            "CyberAgreementSigned": None,
            "EmployeeStatus": "Active",
            "EmployeeType": "Employee",
            "FacilityCode": None,
            "Facility": None,
        }
    ]
    
    with patch(
        "nsls2api.services.bnlpeople_service._call_bnlpeople_webservice",
        new_callable=AsyncMock,
        return_value=mock_api_response,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/v1/person/email/jane.smith@bnl.gov")
    
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["firstname"] == "Jane"
    assert response_json["lastname"] == "Smith"
    assert response_json["email"] == "jane.smith@bnl.gov"
    assert response_json["username"] == "jsmith"
    assert response_json["bnl_employee"] is True



