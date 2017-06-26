from flask import Blueprint, jsonify, request

from ..models import Artist, Album,ndb
from ..helpers.auth import auth_required
from ..helpers.misc import album_genre_lookup

genre_bp = Blueprint('genre', __name__)


'''
  Artist by Genre

  METHODS: GET
  URL_PARAMS: genre_id, page_size, offset
  RETURN: JSON
  DESC: Gets the artist for a specific genre_id.
'''


@genre_bp.route('/artists/<genre_id>', methods=['GET'])
@auth_required()
def hot_artist_in_genre(genre_id):
    page_size =int(request.args.get('page_size')or 30)
    offset = int(request.args.get('offset') or 0)
    hot_albums, more = album_genre_lookup(genre_id,page_size,offset)

    jv_dict = []
    for album in hot_albums:
        a = Artist.query().filter(Artist._key == album.artist_id).get()
        if jv_dict.__contains__(a):
            continue
        jv_dict.append(a)
    return jsonify(hot_artist=jv_dict, has_more=more)


'''
  Albums by Genre

  METHODS: GET
  URL_PARAMS: genre_id, page_size, offset
  RETURN: JSON
  DESC: Gets the Albums for a specific genre_id.
'''


@genre_bp.route('/music/<genre_id>', methods=['GET'])
@auth_required()
def hot_albums_in_genre(genre_id):
    page_size = int(request.args.get('page_size') or 30)
    offset = int(request.args.get('offset') or 30)
    hot_albums, more = album_genre_lookup(genre_id,page_size,offset)
    return jsonify(hot_albums=hot_albums, has_more=more)
