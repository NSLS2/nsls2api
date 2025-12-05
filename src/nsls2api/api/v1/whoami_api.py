from fastapi import APIRouter, Depends, Request, Query
from nsls2api.services.ldap_service import get_user_info, shape_ldap_response
from nsls2api.infrastructure.config import get_settings

router = APIRouter()

@router.get("/whoami")
async def whoami(request: Request, upn: str = Query(..., description="User Principal Name")):
    settings = get_settings()

    LDAP_SERVER = settings.ldap_server
    BASE_DN = settings.base_dn
    BIND_USER = settings.bind_user
    BIND_PASSWORD = settings.ldap_bind_password

    user_info = get_user_info(upn, LDAP_SERVER, BASE_DN, BIND_USER, BIND_PASSWORD)
    
    if not user_info:
        return {"error": "User not found or lookup failed"}

    shaped_info = shape_ldap_response(user_info)
    if shaped_info["identity"]["unix"]["uidNumber"] and shaped_info["identity"]["unix"]["gidNumber"]:
        unix_status = "Unix account present"
    else:
        unix_status = "Unix account not found"

    shaped_info["unix_account_status"] = unix_status
    return {"user": shaped_info}