""" QuotefaultAPI - quotes.py
/quotes
/quotes/<id>
"""

from flask import Blueprint, jsonify, session, request

from quotefault_api import auth
from quotefault_api.models import Quote
from quotefault_api.utils import parse_as_json, create_quote

quotes = Blueprint('quotes', __name__)


@quotes.route('/', methods=['GET', 'POST'])
@auth.oidc_auth
def quotes_route():
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
        return create_quote(submitter, speaker, quote)
    return jsonify({'status': 'error',
                    'message': 'unsupported http method'}), 405
