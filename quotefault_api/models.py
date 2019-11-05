import binascii
import os

from datetime import datetime
from sqlalchemy import UniqueConstraint
from flask_sqlalchemy import SQLAlchemy

from quotefault_api import app

db = SQLAlchemy(app)


class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submitter = db.Column(db.String(80))
    quote = db.Column(db.String(200), unique=True)
    speaker = db.Column(db.String(50))
    quote_time = db.Column(db.DateTime)

    # initialize a row for the Quote table
    def __init__(self, submitter, quote, speaker):
        self.quote_time = datetime.now()
        self.submitter = submitter
        self.quote = quote
        self.speaker = speaker


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer)
    voter = db.Column(db.String(50))
    direction = db.Column(db.Integer)
    updated_time = db.Column(db.DateTime)

    def __init__(self, quote_id, voter, direction):
        self.updated_time = datetime.now()
        self.quote_id = quote_id
        self.voter = voter
        self.direction = direction


class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(64), unique=True)
    owner = db.Column(db.String(80))
    reason = db.Column(db.String(120))
    __table_args__ = (UniqueConstraint('owner', 'reason', name='unique_key'),)

    def __init__(self, owner, reason):
        self.hash = binascii.b2a_hex(os.urandom(10))
        self.owner = owner
        self.reason = reason
