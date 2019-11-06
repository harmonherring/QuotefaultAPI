""" Quotefault - members.py
/members/
/members/cache/
"""
from flask import Blueprint, jsonify, session, request

from quotefault_api import auth
from quotefault_api.ldap import ldap_get_member, ldap_cached_get_all_members, \
    ldap_get_all_members, ldap_is_rtp

members = Blueprint('members', __name__)


@members.route('/', methods=['GET'])
@auth.oidc_auth
def uncached_members():
    return ldap_get_all_members(), 200


@members.route('/cache', methods=['GET', 'DELETE'])
@auth.oidc_auth
def cached_members():
    """
    :GET: Returns cached copy of all users
    :DELETE: Invalidates the cache
    :TODO: refresh cache after it's invalidated
    """
    if request.method == 'GET':
        return ldap_cached_get_all_members(), 200
    if request.method == 'DELETE':
        uid = session['userinfo'].get('preferred_username')
        if ldap_is_rtp(uid):
            ldap_cached_get_all_members.cache_clear()
            ldap_get_member.cache_clear()
            return jsonify({"status": "success"}), 200
        return jsonify({"status": "failure", "message": "unauthorized"}), 403
    return 405
