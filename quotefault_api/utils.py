from datetime import datetime, timedelta

from functools import wraps
from flask import session, jsonify

from quotefault_api.models import db, APIKey, Quote, Vote
from quotefault_api.ldap import ldap_is_member


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


def return_quote_json(quote: Quote, current_user=None):
    """
    Returns a Quote Object as JSON/Dict
    :param quote: The quote object being formatted
    :param current_user: The current user; used to determine whether that use voted on the quote
    :return: Returns a dictionary of the quote object formatted to return as
    JSON
    """
    votes = Vote.query.filter_by(quote_id=quote.id)
    num_votes = sum(vote.direction
                    if vote.quote_id == quote.id
                    else 0 for vote in votes)
    direction = 0
    for vote in votes:
        if vote.quote_id == quote.id and vote.voter == current_user:
            direction = vote.direction

    return {
        'id': quote.id,
        'quote': quote.quote,
        'submitter': quote.submitter,
        'speaker': quote.speaker,
        'quoteTime': quote.quote_time,
        'votes': num_votes,
        'direction': direction
    }


def return_vote(vote: Vote) -> dict:
    return {
        'voter': vote.voter,
        'direction': vote.direction,
        'quote_id': vote.quote_id,
        'updated_time': str(vote.updated_time)
    }


def parse_as_json(quotes: list, quote_json=None, current_user=None) -> list:
    """
    Builds a list of Quotes as JSON to be returned to the user requesting them
    :param quotes: List of Quote Objects
    :param quote_json: List of Quote Objects as dicts to return as JSON
    :param current_user: the currently logged in user
    :return: Returns a list of Quote Objects as dicts to return as JSON
    """
    if quote_json is None:
        quote_json = []
        print("SETTING QUOTE JSON")
    for quote in quotes:
        print(type(quote_json))
        quote_json.append(return_quote_json(quote))
        votes = Vote.query.filter_by(quote_id=quote.id)
        quote_json[len(quote_json) - 1]["votes"] = sum(vote.direction
                                                       if vote.quote_id == quote.id
                                                       else 0 for vote in votes)
        direction = 0
        for vote in votes:
            if vote.quote_id == quote.id and vote.voter == current_user:
                direction = vote.direction
        quote_json[len(quote_json) - 1]["direction"] = direction
    return jsonify(quote_json)


def parse_as_json_with_votes(quotes: list, current_user: str, quote_json=None):
    """
    Parses a quote in the same manner as parse_as_json(), but includes number
    of votes and whether the specified user has voted on a quote
    :param quotes: list of quotes (probably should be a query
    :param current_user: the user currently logged in (lying is not allowed and will be shunned)
    :param quote_json: apparently this is used with the other parse_as_json()...?
    :return: a list of jsonified quotes
    """
    if quote_json is None:
        quote_json = []
    for quote in quotes:
        quote_json.append(return_quote_json(quote))
        votes = Vote.query.filter_by(quote_id=quote.id)
        quote_json[len(quote_json)-1]["votes"] = sum(vote.direction
                                                     if vote.quote_id == quote.id
                                                     else 0 for vote in votes)
        direction = 0
        for vote in votes:
            if vote.quote_id == quote.id and vote.voter == current_user:
                direction = vote.direction
        quote_json[len(quote_json)-1]["direction"] = direction
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


def create_quote(submitter: str, speaker: str, quote: str) -> Quote or dict:
    error = False
    error_message = ""
    if not speaker:
        error = True
        error_message = "missing speaker"
    elif not quote:
        error = True
        error_message = "missing quote"
    elif submitter == speaker:
        error = True
        error_message = "you can't quote yourself"
    elif Quote.query.filter_by(quote=quote).first():
        error = True
        error_message = "quote already exists"
    elif not ldap_is_member(speaker):
        error = True
        error_message = "speaker doesn't exist"
    elif len(quote) > 200:
        error = True
        error_message = "quote is too long"
    if error:
        return jsonify({'status': 'error',
                        'message': error_message}), 422
    new_quote = Quote(submitter, quote, speaker)
    db.session.add(new_quote)
    db.session.flush()
    db.session.commit()
    return return_quote_json(new_quote), 201
