import binascii
from datetime import datetime, timedelta

from ldap3 import Connection, Server

from nsls2api.infrastructure.logging import logger


def to_hex(val):
    if isinstance(val, bytes):
        return binascii.hexlify(val).decode()
    return None

OPERATIONAL_ATTRIBUTES = [
    'manager',
    'objectGUID',
    'objectSid',
    'memberOf',
    'whenCreated',
    'whenChanged',
]

def get_user_info(upn, ldap_server, ldap_base_dn, ldap_bind_user, bind_password):
    conn = None 
    try:
        server = Server(ldap_server)
        conn = Connection(server, user=ldap_bind_user, password=bind_password, auto_bind=True)
        
        search_filter = f"(&(objectclass=person)(userPrincipalName={upn}))"
        conn.search(ldap_base_dn, search_filter, attributes=['sAMAccountName'])

        if not conn.entries:
            logger.warning("No entries found for the given UPN.")
            return None

        entry = conn.entries[0]
        username = entry.sAMAccountName.value if 'sAMAccountName' in entry else None
        if username is None:
            logger.warning("sAMAccountName not found.")
            return None

        search_filter = f"(&(objectclass=posixaccount)(sAMAccountName={username}))"
        
        # Search 1: Get regular attributes
        conn.search(ldap_base_dn, search_filter, attributes=['*'])
        if not conn.entries:
            return None

        entry = conn.entries[0]
        user = _extract_attributes(entry)

        # Search 2: Get operational attributes and merge
        conn.search(ldap_base_dn, search_filter, attributes=OPERATIONAL_ATTRIBUTES)
        if conn.entries:
            entry = conn.entries[0]
            operational = _extract_attributes(entry)
            user.update(operational)

        return user

    except Exception as e:
        logger.error(f"LDAP Error: {e}", exc_info=True)
        return None
    finally:
        if conn is not None:
            conn.unbind()

def _extract_attributes(entry):
    data = {}
    for attribute in entry.entry_attributes:
        value = entry[attribute].value
        if isinstance(value, bytes):
            data[attribute] = value
        elif isinstance(value, list):
            data[attribute] = value
        else:
            data[attribute] = str(value) if value is not None else None
    return data

def filetime_to_str(filetime):
    try:
        if filetime is None or int(filetime) == 0 or int(filetime) == 9223372036854775807:
            return "Never"
        dt = datetime(1601, 1, 1) + timedelta(microseconds=int(filetime) // 10)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(filetime)

def generalized_time_to_str(gt):
    try:
        if not gt:
            return ""
        if isinstance(gt, datetime):
            return gt.strftime("%Y-%m-%d %H:%M:%S UTC")
        gt_str = str(gt)
        dt = datetime.strptime(gt_str.split(".")[0], "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(gt) if gt else ""

def decode_uac(uac):
    flags = []
    try:
        val = int(uac)
        if val & 0x0001: flags.append("SCRIPT")
        if val & 0x0002: flags.append("ACCOUNTDISABLE")
        if val & 0x0008: flags.append("HOMEDIR_REQUIRED")
        if val & 0x0200: flags.append("NORMAL_ACCOUNT")
        if val & 0x1000: flags.append("PASSWORD_EXPIRED")
    except Exception:
        return []
    return flags or ["NORMAL_ACCOUNT"]

def shape_ldap_response(user_info, dn=None, status="Read", read_time=None):
    def clean_groups(groups_val):
        if not groups_val:
            return []
        if isinstance(groups_val, list):
            return [str(g) for g in groups_val]
        elif isinstance(groups_val, str):
            return [g.strip() for g in groups_val.replace("\n", ",").split(",") if g.strip()]
        return []

    def clean_object_class(obj_class_val):
        if not obj_class_val:
            return []
        if isinstance(obj_class_val, list):
            return [str(s).strip() for s in obj_class_val]
        elif isinstance(obj_class_val, str):
            return [s.strip() for s in obj_class_val.replace(",", " ").split() if s.strip()]
        return []

    return {
        "dn": dn or user_info.get("distinguishedName"),
        "status": status,
        "readTime": read_time,
        "identity": {
            "displayName": user_info.get("displayName"),
            "email": user_info.get("mail") or user_info.get("email"),
            "department": user_info.get("department"),
            "manager": user_info.get("manager"),
            "unix": {
                "uid": user_info.get("uid"),
                "uidNumber": user_info.get("uidNumber"),
                "gidNumber": user_info.get("gidNumber"),
                "homeDirectory": user_info.get("homeDirectory"),
                "loginShell": user_info.get("loginShell")
            }
        },
        "account": {
            "accountExpires": filetime_to_str(user_info.get("accountExpires")),
            "badPasswordTime": filetime_to_str(user_info.get("badPasswordTime")),
            "badPwdCount": int(user_info.get("badPwdCount") or 0),
            "pwdLastSet": filetime_to_str(user_info.get("pwdLastSet")),
            "lastLogon": filetime_to_str(user_info.get("lastLogon")),
            "userAccountControlFlags": decode_uac(user_info.get("userAccountControl")),
            "userPrincipalName": user_info.get("userPrincipalName"),
            "logonCount": int(user_info.get("logonCount") or 0),
            "sAMAccountName": user_info.get("sAMAccountName"),
            "sAMAccountType": user_info.get("sAMAccountType"),
            "lastLogoff": filetime_to_str(user_info.get("lastLogoff")),
            "uSNCreated": int(user_info.get("uSNCreated") or 0),
            "uSNChanged": int(user_info.get("uSNChanged") or 0),
        },
        "directory": {
            "objectGUID": to_hex(user_info.get("objectGUID")),
            "objectSid": to_hex(user_info.get("objectSid")),
            "primaryGroupID": user_info.get("primaryGroupID"),
            "distinguishedName": user_info.get("distinguishedName"),
            "whenCreated": generalized_time_to_str(user_info.get("whenCreated")),
            "whenChanged": generalized_time_to_str(user_info.get("whenChanged")),
        },
        "groups": clean_groups(user_info.get("memberOf")),
        "attributes": {
            "sn": user_info.get("sn"),
            "givenName": user_info.get("givenName"),
            "description": user_info.get("description"),
            "gecos": user_info.get("gecos"),
            "street": user_info.get("street"),
            "codePage": user_info.get("codePage"),
            "countryCode": user_info.get("countryCode"),
            "instanceType": user_info.get("instanceType"),
            "objectClass": clean_object_class(user_info.get("objectClass"))
        }
    }