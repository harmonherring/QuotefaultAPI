""" Quotefault - legacy.py
/<api_key>/all
/<api_key>/random
/<api_key>/newest
/<api_key>/between
/<api_key>/markov
/generatekey/<reason>
"""
import random

import markdown
from flask import Blueprint, jsonify, request, json, redirect, url_for
from flask_cors import cross_origin

import markov
from quotefault_api import auth
from quotefault_api.models import db
from quotefault_api.models import Quote, APIKey
from quotefault_api.utils import check_key, query_builder, parse_as_json, \
    return_quote_json, get_metadata, check_key_unique

legacy = Blueprint('legacy', __name__)


@legacy.route('/', methods=['GET'])
def index():
    db.create_all()
    f = open('README.md', 'r')
    return markdown.markdown(f.read(), extensions=['markdown.extensions.fenced_code'])


@legacy.route('/<api_key>/between/<start>/<limit>', methods=['GET'])
@cross_origin(headers=['Content-Type'])
@check_key
def between(start: str, limit: str):
    """
    Shows all quotes submitted between two dates
    :param start: Start date string
    :param limit: End date string
    :return: Returns a JSON list of quotes between the two dates
    """
    submitter = request.args.get('submitter')
    speaker = request.args.get('speaker')
    query = query_builder(start, limit, submitter, speaker)
    if not query.all():
        return "none"
    return parse_as_json(query.all())


@legacy.route('/<api_key>/create', methods=['PUT'])
@cross_origin(headers=['Content-Type'])
@check_key
def create_quote():
    """
    Put request to create a new Quote
    :return: The new Quote object that was created by the request
    """
    # Gets the body of the request and recieves it as JSON
    data = json.loads(request.data.decode('utf-8'))

    if data['quote'] and data['speaker']:
        quote = data['quote']
        submitter = data['submitter']
        speaker = data['speaker']

        if not quote or not speaker or not submitter:
            return "You didn't fill in one of your fields. You literally only had three responsibilities, " \
                   "and somehow you fucked them up.", 400
        if speaker == submitter:
            return "Quote someone else you narcissist.", 400
        if Quote.query.filter(Quote.quote == quote).first() is not None:
            return "That quote has already been said, asshole", 400
        if len(quote) > 200:
            return "Quote is too long! This is no longer a quote, it's a monologue!", 400
        # Creates a new quote given the data from the body of the request
        new_quote = Quote(submitter=submitter, quote=quote, speaker=speaker)
        db.session.add(new_quote)
        db.session.flush()
        db.session.commit()
        # Returns the json of the quote
        return jsonify(return_quote_json(new_quote)), 201
    return "You need to actually fill in your fields.", 400


@legacy.route('/<api_key>/all', methods=['GET'])
@cross_origin(headers=['Content-Type'])
@check_key
def all_quotes():
    """
    Returns all Quotes in the database
    :return: Returns JSON of all quotes in the Quotefault database
    """
    date = request.args.get('date')
    submitter = request.args.get('submitter')
    speaker = request.args.get('speaker')
    query = query_builder(date, None, submitter, speaker)
    if not query.all():
        return "none"
    return parse_as_json(query.all())


@legacy.route('/<api_key>/random', methods=['GET'])
@cross_origin(headers=['Content-Type'])
@check_key
def random_quote():
    """
    Returns a random quote from the database
    :return: Returns a random quote
    """
    date = request.args.get('date')
    submitter = request.args.get('submitter')
    speaker = request.args.get('speaker')
    quotes = query_builder(date, None, submitter, speaker).all()
    if not quotes:
        return "none"
    random_index = random.randint(0, len(quotes))
    return jsonify(return_quote_json(quotes[random_index]))


@legacy.route('/<api_key>/newest', methods=['GET'])
@cross_origin(headers=['Content-Type'])
@check_key
def newest():
    """
    Queries the database for the newest quote, with optional parameters to
    define submitter or datetime stamp
    :return: Returns the newest quote found during the query
    """
    date = request.args.get('date')
    submitter = request.args.get('submitter')
    speaker = request.args.get('speaker')
    query = query_builder(date, None, submitter, speaker).order_by(Quote.id.desc())
    if not query.all():
        return "none"
    return jsonify(return_quote_json(query.first()))


@legacy.route('/<api_key>/<qid>', methods=['GET'])
@cross_origin(headers=['Content-Type'])
@check_key
def quote_id(qid: int):
    """
    Queries the database for the specified quote.
    :param qid: The id of the quote to find
    :return: Returns the specified quote if exists, else 'none'
    """
    query = query_builder(None, None, None, None, id_num=qid)
    if not query.all():
        return "none"
    return jsonify(return_quote_json(query.first()))


@legacy.route('/<api_key>/markov', methods=['GET'])
@cross_origin(headers=['Content-Type'])
@check_key
def markov_single():
    """
    Generates a quote using a markov chain, optionally constraining
    input to a speaker or submitter.
    """
    submitter = request.args.get('submitter')
    speaker = request.args.get('speaker')
    query = query_builder(None, None, submitter, speaker)
    if query.all() is None:
        return "none"
    markov.reset()
    markov.parse([quote.quote for quote in query.all()])
    return jsonify(markov.generate())


@legacy.route('/<api_key>/markov/<count>', methods=['GET'])
@cross_origin(headers=['Content-Type'])
@check_key
def markov_list(count: int):
    """
    Generates a list of quotes using a markov chain, optionally constraining
    input to a speaker or submitter.
    """
    submitter = request.args.get('submitter')
    speaker = request.args.get('speaker')
    query = query_builder(None, None, submitter, speaker)
    if query.all() is None:
        return "none"
    markov.reset()
    markov.parse([quote.quote for quote in query.all()])
    return jsonify(markov.generate_list(int(count)))


@legacy.route('/generatekey/<reason>')
@auth.oidc_auth
def generate_api_key(reason: str):
    """
    Creates an API key for the user requested.
    Using a reason and the username grabbed through the @auth.oidc_auth call
    :param reason: Reason for the API key
    :return: Hash of the Key or a String stating an error
    """
    metadata = get_metadata()
    if not check_key_unique(metadata['uid'], reason):
        # Creates the new API key
        new_key = APIKey(metadata['uid'], reason)
        # Adds, flushes and commits the new object to the database
        db.session.add(new_key)
        db.session.flush()
        db.session.commit()
        return new_key.hash
    return "There's already a key with this reason for this user!"


@legacy.route('/logout')
@auth.oidc_logout
def logout():
    return redirect(url_for('index'), code=302)
