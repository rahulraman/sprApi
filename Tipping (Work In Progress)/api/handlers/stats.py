from ..models import Artist, Album, Track
from ..errors import APIException
from google.appengine.ext import ndb

from flask import Blueprint, jsonify, request

stats_bp = Blueprint('status', __name__)


'''
      Search Artist

  METHODS: GET
  RETURN: JSON
  DESC: A simple database stats
endpoints for displaying statistics
'''


@stats_bp.route('/')
def hello():
    if not request.args.get('key') or request.args.get('key') != 'sOOperS3cr3tStats':
        raise APIException('Unable to locate correct stats page.', status_code=400)

    data = dict()

    data['total_artists'] = Artist.query().count()
    data['total_albums'] = Album.query().count()
    data['total_tracks'] = Track.query().count()

    files_count = 0
    for track in Track.query().fetch():
        if track.source_file:
            files_count += 1

    data['total_tracks_uploaded'] = files_count

    data['artist_detail'] = dict()

    for artist in Artist.query().fetch():
        data['artist_detail'][artist.name] = dict(
            total_albums=Album.query(Album.artist_id == artist.key).count(),
            total_tracks=Track.query(Track.artist_id == artist.key).count()
        )

    return jsonify(data)