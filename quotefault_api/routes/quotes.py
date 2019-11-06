""" QuotefaultAPI - quotes.py
/quotes
/quotes/<id>
"""

from flask import Blueprint, jsonify, session, request

from quotefault_api import auth
from quotefault_api.models import db, Quote
from quotefault_api.ldap import ldap_is_rtp
from quotefault_api.utils import parse_as_json, flask_create_quote, return_quote_json, \
    ldap_is_member

quotes = Blueprint('quotes', __name__)


@quotes.route('/', methods=['GET', 'POST'])
@auth.oidc_auth
def quotes_route():  # pylint: disable=inconsistent-return-statements
    if request.method == 'GET':
        speaker = request.args.get("speaker")
        submitter = request.args.get("submitter")
        quote = request.args.get("quote")
        current_user = session['userinfo'].get('preferred_username')

        if request.args.get("page_id"):
            page_id = int(request.args.get("page_id"))
        else:
            page_id = 0
        if request.args.get("page_size"):
            page_size = int(request.args.get("page_size"))
        else:
            page_size = 10

        query = Quote.query.order_by(Quote.quote_time.desc())

        if quote:
            query = query.filter(Quote.quote.ilike("%" + quote + "%"))
        if speaker:
            query = query.filter(Quote.speaker.ilike("%" + speaker + "%"))
        if submitter:
            query = query.filter(Quote.submitter.ilike("%" + submitter + "%"))

        query = query[page_id * page_size: page_id + 1 * page_size]
        return parse_as_json(query, current_user=current_user), 200
    if request.method == 'POST':
        if request.content_type == 'application/json':
            data = request.get_json()
            quote = data.get('quote')
            speaker = data.get('speaker')
        elif request.content_type == 'application/x-www-form-urlencoded':
            quote = request.args.get('quote')
            speaker = request.args.get('speaker')
        else:
            return jsonify({'status': 'error',
                            'message': 'unsupported content-type'}), 415
        submitter = session['userinfo'].get('preferred_username')
        return flask_create_quote(submitter, speaker, quote)


@quotes.route('/<qid>', methods=['GET', 'PUT', 'DELETE'])
@auth.oidc_auth
def quote_route(qid: int):  # pylint: disable=inconsistent-return-statements,too-many-return-statements
    """
    Gets, modifies or deletes a singular quote
    :param qid: specifies the quote being modified
    :return: quote after modification
    """
    current_user = session['userinfo'].get('preferred_username')
    quote = Quote.query.filter_by(id=qid).first()

    if not quote:
        return jsonify({'status': 'error',
                        'message': 'quote doesn\'t exist'}), 404

    if request.method == 'GET':
        return return_quote_json(quote, current_user=current_user), 200

    if not (current_user == quote.submitter or ldap_is_rtp(current_user)):
        return jsonify({'status': 'error',
                        'message': 'not authorized to modify quote'}), 403

    if request.method == 'PUT':
        if request.content_type == 'application/json':
            data = request.get_json()
            new_quote = data.get('quote')
            speaker = data.get('speaker')
        elif request.content_type == 'application/x-www-form-urlencoded':
            new_quote = request.args.get('quote')
            speaker = request.args.get('speaker')
        else:
            return jsonify({'status': 'error',
                            'message': 'unsupported content-type'}), 415
        if speaker:
            if ldap_is_member(speaker):
                quote.speaker = speaker
            else:
                return jsonify({'status': 'error',
                                'message': 'invalid speaker'}), 422
        if new_quote:
            quote.quote = new_quote
        db.session.flush()
        db.session.commit()
        return return_quote_json(quote, current_user=current_user), 201

    if request.method == 'DELETE':
        Quote.query.filter_by(id=qid).delete()
        db.session.flush()
        db.session.commit()
        return jsonify({'status': 'success',
                        'message': 'quote successfully deleted'}), 201
