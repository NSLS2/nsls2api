from fastapi import APIRouter, Depends, Request
from nsls2api.services.ldap_service import get_user_info
router = APIRouter()

@router.get("/whoami")
async def whoami(request: Request):
    #ldap logic
    LDAP_SERVER = "ldap://ldapproxy.nsls2.bnl.gov"
    BASE_DN = "dc=bnl,dc=gov"
    BIND_USER = "CN=n2snbind3,OU=CAM - Service Accounts,OU=CAM,DC=bnl,DC=gov"
    BIND_PASSWORD = "V3%aKntg8woNa*b3#J"
    upn = "swilkins@bnl.gov"

    user_info = get_user_info(upn, LDAP_SERVER, BASE_DN, BIND_USER, BIND_PASSWORD)
    return {"user": user_info}