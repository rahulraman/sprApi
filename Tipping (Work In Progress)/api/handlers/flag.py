from flask import request, Blueprint, g, jsonify
from ..models import Flag
from .auth import auth_required
from google.appengine.ext import ndb
from ..errors import ValidationException

flag_bp = Blueprint('flag', __name__)

@flag_bp.route('/', methods=['POST'])
@auth_required()
def flag_item():
    # if not request.json.get('album_id') or not request.json.get('artist_id'):
    #     raise ValidationException(payload=['album_id','artist_id'])
    album = None
    if request.json.get('album_id'):
        album = ndb.Key(urlsafe=request.json.get('album_id'))

    artist = None
    if request.json.get('artist_id'):
        artist = ndb.Key(urlsafe=request.json.get('artist_id'))

    reason = ""
    if request.json.get('reason'):
        reason = request.json.get('reason')

    flag = Flag(flagger=g.user.key, album=album,artist=artist, reason=reason)

    flag.put()

    return jsonify(flag=flag)