from ldap3 import Server, Connection

def get_user_info(upn, ldap_server, base_dn, bind_user, bind_password):
    conn = None 
    try:
        server = Server(ldap_server)
        conn = Connection(server, user=bind_user, password=bind_password, auto_bind=True)
        search_filter = f"(&(objectclass=person)(userPrincipalName={upn}))"
        conn.search(base_dn, search_filter, attributes=['sAMAccountName'])
        if conn.entries:
            entry = conn.entries[0]
        else:
            print("No entries found for the given UPN.")
            if conn is not None:
                conn.unbind()
            return None
        username = entry.sAMAccountName.value if 'sAMAccountName' in entry else None
        print(f"Resolved username: {username}")
        if username is None:
            if conn is not None:
                conn.unbind()
            return None
        search_filter = f"(&(objectclass=posixaccount)(sAMAccountName={username}))"
        conn.search(base_dn, search_filter, attributes=['*'])
        print('posix search result:",conn.entries')
        if conn.entries:
            entry = conn.entries[0]
            if conn is not None:
                conn.unbind()
            user = dict()
            for attribute in entry.entry_attributes:
                user[attribute] = str(entry[attribute].value)
            return user
        else:
            print("no posix entries found for the given username.")
    except Exception as e:
        print(f"LDAP Error: {e}")
        if conn is not None:
            conn.unbind()
        return None
    if conn is not None:
        conn.unbind()
    return None