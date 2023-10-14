import json

from flask import Flask, render_template_string
from flask_cors import CORS

from .routes import rest_api
from .models import db
from flask_uploads import UploadSet, IMAGES, configure_uploads

from flask_mail import Mail

from flask_session import Session


sess = Session()

images = UploadSet("photos", IMAGES)

app = Flask(__name__)

app.config.from_object("api.config.BaseConfig")
mail = Mail()
db.init_app(app)
rest_api.init_app(app)
mail.init_app(app)
CORS(app)
configure_uploads(app, images)
sess.init_app(app)


# Setup database
@app.before_first_request
def initialize_database():
    db.create_all()


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template_string("PageNotFound {{ errorCode }}", errorCode="404")


"""
   Custom responses
"""


@app.after_request
def after_request(response):
    """
    Sends back a custom error with {"success", "msg"} format
    """

    if int(response.status_code) >= 400:
        response_data = json.loads(response.get_data())
        if "errors" in response_data:
            response_data = {
                "success": False,
                "msg": list(response_data["errors"].items())[0][1],
            }
            response.set_data(json.dumps(response_data))
        response.headers.add("Content-Type", "application/json")

    return response
