import logging

import pytest
from httpx import ASGITransport, AsyncClient

from nsls2api.infrastructure.security import (
    API_KEY_PREFIX,
    generate_api_key,
    lookup_api_key,
)
from nsls2api.main import app
from nsls2api.models.apikeys import ApiKey

APP_LOGGER = "uvicorn.error.nsls2api"


def first_eight(key: str) -> str:
    return key[len(API_KEY_PREFIX) : len(API_KEY_PREFIX) + 8]


@pytest.mark.anyio
async def test_key_in_the_url_still_authenticates_and_is_flagged(admin_api_key, caplog):
    key = admin_api_key["key"]

    with caplog.at_level(logging.WARNING, logger=APP_LOGGER):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/v1/admin/validate", params={"api_key": key})

    assert response.status_code == 200
    assert response.json() == "test_admin"

    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "deprecated" in warnings[0]
    assert "GET /v1/admin/validate" in warnings[0]
    assert "api_key" not in warnings[0]
    assert key not in caplog.text


@pytest.mark.anyio
async def test_key_in_the_header_is_not_flagged(admin_api_key, caplog):
    key = admin_api_key["key"]

    with caplog.at_level(logging.WARNING, logger=APP_LOGGER):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                "/v1/admin/validate", headers={"Authorization": key}
            )

    assert response.status_code == 200
    assert response.json() == "test_admin"
    assert "deprecated" not in caplog.text


@pytest.mark.anyio
async def test_invalid_key_in_the_url_is_still_rejected(caplog):
    with caplog.at_level(logging.WARNING, logger=APP_LOGGER):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                "/v1/admin/validate", params={"api_key": f"{API_KEY_PREFIX}nonesuch"}
            )

    assert response.status_code == 401
    assert "nonesuch" not in caplog.text


def test_openapi_marks_the_query_parameter_deprecated():
    schemes = app.openapi()["components"]["securitySchemes"]

    query_schemes = [s for s in schemes.values() if s.get("in") == "query"]
    assert len(query_schemes) == 1
    assert query_schemes[0]["name"] == "api_key"
    assert "Deprecated" in query_schemes[0]["description"]
    assert "Authorization header" in query_schemes[0]["description"]


@pytest.mark.anyio
async def test_lookup_error_does_not_contain_the_key():
    unknown = f"{API_KEY_PREFIX}{'ab' * 36}"

    with pytest.raises(LookupError) as error:
        await lookup_api_key(unknown)

    assert unknown not in str(error.value)
    assert first_eight(unknown) not in str(error.value)


@pytest.mark.anyio
async def test_rotation_logs_only_the_username_and_first_eight(api_key, caplog):
    old_key = api_key["key"]
    old_record = await ApiKey.find_one(ApiKey.first_eight == first_eight(old_key))
    assert old_record.valid

    with caplog.at_level(logging.INFO, logger=APP_LOGGER):
        new_key = await generate_api_key(username="test_user")

    assert f"Invalidating old key {first_eight(old_key)} for user test_user" in (
        caplog.text
    )
    assert old_record.hashed_key not in caplog.text
    assert old_key not in caplog.text
    assert new_key["key"] not in caplog.text

    old_record = await ApiKey.find_one(ApiKey.first_eight == first_eight(old_key))
    assert not old_record.valid
