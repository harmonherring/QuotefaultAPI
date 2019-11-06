from functools import lru_cache
from csh_ldap import CSHMember

from quotefault_api import _ldap


@lru_cache(maxsize=8192)
def ldap_cached_get_all_members() -> dict:
    """
    :return: Cached list of all ldap 'members'. If the cache is empty and more than one person
    tries to use this function, Python will core dump.
    :TODO: Add a lock for this function so the above problem doesn't happen
    """
    return {member.uid: member.cn for member in _ldap.get_group('member').get_members()}


def ldap_get_all_members() -> dict:
    """
    :return: Non-cached list of all ldap 'members'.
    """
    return {member.uid: member.cn for member in _ldap.get_group('member').get_members()}


@lru_cache(maxsize=8192)
def ldap_get_member(username: str) -> CSHMember:
    """
    Gets one member from ldap using their username
    :param username: username of the desired member
    :return: CSHMember object representing the user
    """
    return _ldap.get_member(username, uid=True)


def _ldap_is_member_of_group(member: CSHMember, group: str) -> bool:
    """
    Checks to see if a CSHMember is part of the specified ldap group
    :param member: CSHMember whose group is in question
    :param group: group to check
    :return: True if member is in group, False otherwise
    """
    group_list = member.get("memberOf")
    for group_dn in group_list:
        if group == group_dn.split(",")[0][3:]:
            return True
    return False


def ldap_is_member(username: str) -> bool:
    """
    Checks to see if a username is a member
    :param username: username of the member you're checking for the existence of
    :return: True if member exists, Fale otherwise
    """
    try:
        _ldap.get_member(username, uid=True)
    except KeyError:
        return False
    return True


def ldap_is_rtp(username: str) -> bool:
    """
    Checks to see if a user is an rtp
    :param username: username of the possible rtp
    :return: True if the user is an rtp, False otherwise
    """
    account = ldap_get_member(username)
    return _ldap_is_member_of_group(account, "rtp")
