from datetime import datetime, timedelta

from functools import wraps, lru_cache
from flask import session, jsonify

from quotefault_api import _ldap
from quotefault_api.models import APIKey, Quote


def check_key(func):
    """
    Creates a wrapper for 'func'.
    Checks if the api key is valid. If it is, return the result of the function.
    If not, return an error message.
    :param func: The function that needs authorisation
    :return: The result of the function or 403 error
    """
    @wraps(func)
    def wrapper(api_key, *args, **kwargs):
        keys = APIKey.query.filter_by(hash=api_key).all()
        if keys:
            return func(*args, **kwargs)
        return "Invalid API Key!", 403
    return wrapper


def get_metadata() -> dict:
    """
    Gets user metadata to return to each route that requests it
    :return: Returns a dict of metadata
    """
    uuid = str(session["userinfo"].get("sub", ""))
    uid = str(session["userinfo"].get("preferred_username", ""))
    metadata = {
        "uuid": uuid,
        "uid": uid
    }
    return metadata


def return_json(quote: Quote):
    """
    Returns a Quote Object as JSON/Dict
    :param quote: The quote object being formatted
    :return: Returns a dictionary of the quote object formatted to return as
    JSON
    """
    return {
        'id': quote.id,
        'quote': quote.quote,
        'submitter': quote.submitter,
        'speaker': quote.speaker,
        'quoteTime': quote.quote_time,
    }


def parse_as_json(quotes: list, quote_json=None) -> list:
    """
    Builds a list of Quotes as JSON to be returned to the user requesting them
    :param quotes: List of Quote Objects
    :param quote_json: List of Quote Objects as dicts to return as JSON
    :return: Returns a list of Quote Objects as dicts to return as JSON
    """
    if quote_json is None:
        quote_json = []
    for quote in quotes:
        quote_json.append(return_json(quote))
    return jsonify(quote_json)


def check_key_unique(owner: str, reason: str) -> bool:
    keys = APIKey.query.filter_by(owner=owner, reason=reason).all()
    if keys:
        return True
    return False


def str_to_datetime(date: str) -> datetime:
    """
    Converts a string in either yyyymmdd or mm-dd-yyyy format to a datetime object
    :param date: the date string
    :return: a datetime object equivalent to the date string
    """
    str_format = "%Y%m%d"
    # hyphen characters are used to differentiate between the two formats
    if "-" in date:
        str_format = "%m-%d-%Y"

    return datetime.strptime(date, str_format)


def query_builder(start: str, end: str, submitter: str, speaker: str, id_num=-1):
    """
    Builds a sqlalchemy query.
    :param start: (optional, unless end provided) The date string for the start of the desired range.
    If end is not provided, start specifies a single day's fiter
    :param end: (optional) The date string for the end of the desired range.
    :param submitter: (optional) The CSH username of the submitter to search for.
    :param id_num: (optional) The id of the quote to access from the database.
    :return: The query as defined by the given parameters
    """
    query = Quote.query

    # If an ID is specified, we only need one quote. Don't bother with the other filtering
    if id_num != -1:
        return query.filter_by(id=id_num)

    if start is not None:
        start = str_to_datetime(start)
        if end is not None:
            end = str_to_datetime(end)
        else:
            end = start + timedelta(1)
        query = query.filter(Quote.quote_time.between(start, end))

    if submitter is not None:
        query = query.filter_by(submitter=submitter)

    if speaker is not None:
        query = query.filter_by(speaker=speaker)

    return query


@lru_cache(maxsize=8192)
def ldap_cached_get_all_members():
    return {member.uid: member.cn for member in _ldap.get_group('member').get_members()}


def ldap_get_all_members():
    return {member.uid: member.cn for member in _ldap.get_group('member').get_members()}


@lru_cache(maxsize=8192)
def ldap_get_member(username: str):
    return _ldap.get_member(username, uid=True)


def _ldap_is_member_of_group(member, group):
    group_list = member.get("memberOf")
    for group_dn in group_list:
        if group == group_dn.split(",")[0][3:]:
            return True
    return False


def ldap_is_rtp(account):
    return _ldap_is_member_of_group(account, "rtp")
