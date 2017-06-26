import logging
import stripe
from flask import Flask, request,jsonify
from werkzeug.exceptions import default_exceptions

from .handlers.misc import misc_bp
from .handlers.auth import auth_bp
from .handlers.album import album_bp
from .handlers.artist import artist_bp
from .handlers.comment import comment_bp
from .handlers.track import track_bp
from .handlers.featured import featured_bp
from .handlers.genre import genre_bp
from .handlers.search import search_bp
from .handlers.tasks import tasks_bp
from .handlers.update_schema_handler import update_schema_bp
from .handlers.stats import stats_bp
from .handlers.flag import flag_bp
from .errors import handle_api_error, APIException
from .utils import CustomJSONEncoder
from .config import STRIPE_KEY

logger = logging.getLogger(__name__)


# A method that creates the main app.
def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')

    app.json_encoder = CustomJSONEncoder

    # Hack-ish way to handle Exceptions through our custom handler.
    app.errorhandler(Exception)(handle_api_error)

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = handle_api_error

    app.register_blueprint(misc_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(artist_bp, url_prefix='/artist')
    app.register_blueprint(album_bp, url_prefix='/album')
    app.register_blueprint(comment_bp, url_prefix='/comment')
    app.register_blueprint(track_bp, url_prefix='/track')
    app.register_blueprint(featured_bp, url_prefix='/featured')
    app.register_blueprint(genre_bp, url_prefix='/genre')
    app.register_blueprint(search_bp, url_prefix='/search')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(stats_bp, url_prefix='/status')
    app.register_blueprint(update_schema_bp, url_prefix='/update_schema')
    app.register_blueprint(flag_bp, url_prefix='/flag')

    @app.route('/_ah/health', methods=['GET'])
    def health_handler():
        response = jsonify("")
        response.status_code = 200
        return response
    stripe.api_key = STRIPE_KEY

    return app

app = create_app()


# A post-request wrapper that adds a header.
@app.after_request
def add_cors(resp):
    """ Ensure all responses have the CORS headers. This ensures any failures are also accessible
        by the client. """
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET, PUT'
    resp.headers['Access-Control-Allow-Headers'] = request.headers.get(
        'Access-Control-Request-Headers', 'Authorization')
    # set low for debugging
    if app.debug:
        resp.headers['Access-Control-Max-Age'] = '1'
    return resp
