import os

import csh_ldap
from flask import Flask
from flask_pyoidc.flask_pyoidc import OIDCAuthentication

app = Flask(__name__)

if os.path.exists(os.path.join(os.getcwd(), "config.py")):
    app.config.from_pyfile(os.path.join(os.getcwd(), "config.py"))
else:
    app.config.from_pyfile(os.path.join(os.getcwd(), "config.env.py"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
auth = OIDCAuthentication(
    app,
    issuer=app.config['OIDC_ISSUER'],
    client_registration_info=app.config['OIDC_CLIENT_CONFIG'])
_ldap = csh_ldap.CSHLDAP(app.config["LDAP_DN"], app.config["LDAP_PW"])
app.secret_key = 'submission'

# pylint: disable=wrong-import-position
from quotefault_api.legacy import legacy
from quotefault_api.members import members
# pylint: enable=wrong-import-position

app.register_blueprint(legacy)
app.register_blueprint(members, url_prefix='/members')
