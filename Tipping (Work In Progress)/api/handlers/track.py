import datetime

from flask import Blueprint, jsonify, g, request
from google.appengine.api import images
from google.appengine.ext import ndb

from ..models import Artist, Album, Track, CurrencyValue
from ..helpers.auth import auth_required
from ..helpers.aws import generate_track_upload_url, generate_track_playback_url
from ..errors import APIException, NotAllowedException, NotFoundException, ValidationException
from ..helpers.misc import increment_plays
from ..utils import validate_params

track_bp = Blueprint('track', __name__)


'''
  Create Track

  METHODS: POST
  PARAMS: artist_id, title, explicit
  OPTIONAL: price
  RETURN: JSON
  DESC: Creates an Track object and puts that object in the db.
'''


@track_bp.route('/', methods=['POST'])
@auth_required()
def create_track():
    validate_params(['artist_id', 'title', 'explicit'])
    artist_id = request.json.get('artist_id')
    title = request.json.get('title')

    artist = ndb.Key(urlsafe=artist_id).get()

    if request.json.get('price'):
        price = CurrencyValue(amount=request.json.get('price').get('amount'),
                              currency=request.json.get('price').get('currency'))
    else:
        price = None

    explicit = request.json.get('explicit')


    # Perform some basic checks
    artist = ndb.Key(urlsafe=artist_id).get()
    if not artist or not isinstance(artist, Artist) or artist.owner != g.user.key:
        raise NotAllowedException('Invalid request.', 400)

    new_track = Track(artist_id=artist.key,
                      artist_name=artist.name,
                      title=title,
                      price=price,
                      explicit=explicit)
    new_track.put()

    return jsonify(track=new_track)


'''
  Update Track

  METHODS: POST
  PARAMS: artist_id, title
  URL_PARAMS: track_key
  OPTIONAL: price, explicit
  RETURN: JSON
  DESC: Updates a track object in the database.
'''


@track_bp.route('/<track_key>', methods=['PUT'])
@auth_required()
def update_track(track_key):
    validate_params(['title'])
    track = ndb.Key(urlsafe=track_key).get()
    if not track or not isinstance(track, Track):
        raise NotFoundException("Unable to find the track with the key you provided.")

    updated_fields = dict()
    updated_fields['title'] = request.json.get('title')

    if request.json.get('price'):
        updated_fields['price'] = CurrencyValue(amount=request.json.get('price').get('amount'),
                                                currency=request.json.get('price').get('currency'))

    updated_fields['explicit'] = request.json.get('explicit')


    track.from_dict(updated_fields)
    track.put()

    return jsonify(track=track)


'''
  Upload Track

  METHODS: POST
  PARAMS: filename
  URL_PARAMS: track_key
  RETURN: JSON
  DESC: A Multi-part request that uploads a track to s3 and creates a url for the tracks and adds it to the database.
'''


@track_bp.route('/<track_key>/upload', methods=['POST'])
@auth_required()
def upload_track(track_key):
    validate_params(['filename'])
    track = ndb.Key(urlsafe=track_key).get()
    if not track or not isinstance(track, Track):
        raise NotFoundException("Unable to find the track with the key you provided.")

    filename = request.json.get('filename')
    if not filename or len(filename.split('.')) <= 1:
        raise ValidationException('Improper request, incorrect filename', 400)

    # Assume the file extension is the last element separated by a period
    file_ext = filename.split('.')[-1]

    # Generate the reference and signed URLs
    upload_filename = '{}.{}'.format(track_key, file_ext)
    track.source_file = upload_filename
    track.put()

    upload_url = generate_track_upload_url(upload_filename)


    return jsonify(upload_url=upload_url)


'''
  Playback URL

  METHODS: GET
  URL_PARAMS: track_key
  RETURN: JSON
  DESC: Get the playback url for a track.
'''


@track_bp.route('/<track_key>/playback', methods=['GET'])
@auth_required()
def track_playback_url(track_key):
    rv = ndb.Key(urlsafe=track_key).get()
    if not isinstance(rv, Track):
        raise NotFoundException("Unable to find the track with the key you provided.")
    increment_plays(track_key)
    return jsonify(url=generate_track_playback_url(rv.source_file))


'''
  Get Track

  METHODS: GET
  URL_PARAMS: track_key
  RETURN: JSON
  DESC: Get the the track object for a particular track.
'''


@track_bp.route('/<track_key>', methods=['GET'])
@auth_required()
def fetch_track(track_key):
    rv = ndb.Key(urlsafe=track_key).get()
    return jsonify(track=rv if isinstance(rv, Track) else None)


'''
  Get Artist's Tracks

  METHODS: GET
  URL_PARAMS: artist_key
  RETURN: JSON
  DESC: Get the tracks for a particular artist.
'''


@track_bp.route('/artist/<artist_key>', methods=['GET'])
@auth_required()
def fetch_tracks_by_artist(artist_key):
    return jsonify(tracks=Track.query(Track.artist_id == ndb.Key(urlsafe=artist_key)).fetch())

'''
  Get Tracks for an Album

  METHODS: GET
  URL_PARAMS: track_key
  RETURN: JSON
  DESC: Get the album for a track.
'''


@track_bp.route('/<track_id>/album', methods=['GET'])
@auth_required()
def get_track_album(track_id):
    album = Album.query().filter(Album.tracks == ndb.Key(urlsafe=track_id)).get()
    return jsonify(album=album)

'''
        Play Analytics
    METHODS: POST
    PARAMS: track_id
    RETURN: JSON
    DESC: Increments track plays for analytics. 
'''


@track_bp.route('/play/', methods=['POST'])
@auth_required()
def post_analytics():
    validate_params(['track_id'])
    increment_plays(request.json.get('track_id'))
    return jsonify(success="success")

'''
        Remove track by Key
    METHODS: DELETE
    URL_PARAMS: track_key
    RETURN: JSON
    DESC: Deletes an track from the datastore and removes that track from the album.
'''


@track_bp.route('/<track_key>', methods=['DELETE'])
@auth_required()
def delete_track(track_key):
    track = ndb.Key(urlsafe=track_key).get()
    if not track or not isinstance(track, Track):
        raise NotFoundException("Unable to find the track you are looking for.")
    track_albums = Album.query().filter(Album.tracks == track.key).fetch()
    for a in track_albums:
        a.tracks.remove(track.key)
        a.put()
    track.key.delete()
    return jsonify(success="success")
