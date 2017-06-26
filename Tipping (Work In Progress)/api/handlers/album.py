import datetime
from flask import Blueprint, jsonify, g, request
from google.appengine.api import images
from google.appengine.ext import ndb

from ..models import Artist, Album, TypedURL, CurrencyValue, Track
from ..helpers.auth import auth_required
from ..helpers.aws import save_album_cover
from ..errors import ValidationException, NotAllowedException, ImageException, NotFoundException
from ..utils import validate_params
from boto.s3.connection import S3Connection
from flask import current_app

album_bp = Blueprint('album', __name__)


'''
          Create Album

  METHODS: POST
  PARAMS: artist_id, title, release_date, description, genre_id
  OPTIONAL: price, tracks
  RETURN: JSON
  DESC: Creates an Album object and puts that object in the db.
'''


@album_bp.route('/', methods=['POST'])
@auth_required()
def create_album():
    validate_params(['artist_id', 'title', 'release_date', 'description', 'genre_id'])
    artist_id = request.json.get('artist_id')
    title = request.json.get('title')

    release_date_raw = request.json.get('release_date')
    release_date = datetime.datetime.utcfromtimestamp(release_date_raw) if release_date_raw else datetime.datetime.utcnow()

    if request.json.get('price'):
        price = CurrencyValue(amount=request.json.get('price').get('amount'),
                              currency=request.json.get('price').get('currency'))
    else:
        price = None

    description = request.json.get('description')

    conn = S3Connection(current_app.config['AWS_ACCESS_KEY'], current_app.config['AWS_SECRET_KEY'])
    b = conn.get_bucket(current_app.config['SOURCE_TRACK_S3_BUCKET'])
    if request.json.get('tracks'):
        tracks_array = request.json.get('tracks')
        tracks_dict = {int(t.get('position')): t.get('track_id') for t in tracks_array}
        #tracks = [ndb.Key(urlsafe=value) for (key, value) in sorted(tracks_dict.items())]
        tracks = []
        for (key,value) in sorted(tracks_dict.items()):
            track = ndb.Key(urlsafe=value).get()
            if not track or not isinstance(track, Track):
                continue
            if track.is_active:
                tracks.append(ndb.Key(urlsafe=value))
            else:
                aws_file = b.get_key(key_name=track.source_file)
                if aws_file:
                    track.is_active = True
                    tracks.append(ndb.Key(urlsafe=value))
                    track.put()

    else:
        tracks = []

    genre_id = request.json.get('genre_id')

    # Perform some basic checks
    artist = ndb.Key(urlsafe=artist_id).get()
    if not artist or not isinstance(artist, Artist) or artist.owner != g.user.key:
        raise ValidationException('Invalid Artist, unable to validate the artist provided.')

    artist_name = artist.name

    new_album = Album(artist_id=artist.key,
                      artist_name=artist_name,
                      title=title,
                      release_date=release_date,
                      price=price,
                      description=description,
                      tracks=tracks,
                      genre_id=genre_id)
    new_album.put()

    # Reprocess the JSON output so it matches the input
    rv_dict = new_album.to_dict(exclude=getattr(new_album, 'default_exclude', None))
    rv_dict['_key'] = new_album.key.urlsafe()
    rv_dict['tracks'] = [{'position': k, 'track_id': v} for (k, v) in enumerate(tracks)]
    rv_dict['artist'] = new_album.artist_id.get()

    return jsonify(album=rv_dict)


'''
          Update Album

  METHODS: PUT
  PARAMS: artist_id, title, release_date, description, genre_id#
  URL_PARAMS: album_key
  OPTIONAL: price, tracks
  RETURN: JSON
  DESC: Updates the Album object in the database.
'''


@album_bp.route('/<album_key>', methods=['PUT'])
@auth_required()
def update_album(album_key):
    album = ndb.Key(urlsafe=album_key).get()
    if not album or not isinstance(album, Album):
        raise NotAllowedException()

    updated_fields = dict()
    updated_fields['title'] = request.json.get('title')
    updated_fields['description'] = request.json.get('description')

    release_date_raw = request.json.get('release_date')
    if release_date_raw:
        updated_fields['release_date'] = datetime.datetime.utcfromtimestamp(release_date_raw) if release_date_raw else datetime.datetime.utcnow()

    if request.json.get('price'):
        updated_fields['price'] = CurrencyValue(amount=request.json.get('price').get('amount'),
                                                currency=request.json.get('price').get('currency'))
    conn = S3Connection(current_app.config['AWS_ACCESS_KEY'], current_app.config['AWS_SECRET_KEY'])

    b = conn.get_bucket(current_app.config['SOURCE_TRACK_S3_BUCKET'])
    if request.json.get('tracks'):
        tracks_dict = {int(t.get('position')): t.get('track_id') for t in request.json.get('tracks')}
        #updated_fields['tracks'] = [ndb.Key(urlsafe=value) for (key, value) in sorted(tracks_dict.items())]
        tracks = []
        for (key,value) in sorted(tracks_dict.items()):
            track = ndb.Key(urlsafe=value).get()
            if not track or not isinstance(track,Track):
                continue
            if track.is_active:
                tracks.append(ndb.Key(urlsafe=value))
            else:
                aws_file = b.get_key(key_name=track.source_file)
                if aws_file:
                    track.is_active = True
                    tracks.append(ndb.Key(urlsafe=value))
                    track.put()

        updated_fields['tracks'] = tracks
        if tracks and album.cover_art:
            updated_fields['is_active'] = True
        else:
            updated_fields['is_active'] = False
    else:
        updated_fields['tracks'] = []
        updated_fields['is_active'] = False

    updated_fields['genre_id'] = int(request.json.get('genre_id') or album.genre_id)

    album.from_dict(updated_fields)
    album.put()

    # Reprocess the JSON output so it matches the input
    rv_dict = album.to_dict(exclude=getattr(album, 'default_exclude', None))
    rv_dict['_key'] = album.key.urlsafe()
    rv_dict['tracks'] = [{'position': k, 'track_id': v} for (k, v) in enumerate(album.tracks)]
    rv_dict['artist'] = album.artist_id.get()

    return jsonify(album=rv_dict)


'''
       Post Album Cover

  METHODS: POST
  PARAMS: cover
  URL_PARAMS: album_key
  RETURN: JSON
  DESC: A Multi-part request that creates a url for an image and adds that url to an album.
'''


@album_bp.route('/<album_key>/cover', methods=['POST'])
@auth_required()
def update_cover_art(album_key):
    album = ndb.Key(urlsafe=album_key).get()
    if not album or not isinstance(album, Album):
        raise NotFoundException("Unable to find the album you are looking for, please try again.")

    # Process the image
    uploaded_image = request.files.get('cover')
    if not uploaded_image:
        album.key.delete()
        raise ImageException(description='The image you tried to upload was not in '
                                         'the correct format, Please Try Again.')

    image = images.Image(uploaded_image.read())

    if image.height < 1024 or image.width < 1024:
        album.key.delete()
        raise ImageException(description='The image you tried to upload was too small, please try again.')

    # Scale to ensure the smallest dimension is 1024px
    image.resize(width=1024, height=1024, crop_to_fit=True)
    output_image = image.execute_transforms(output_encoding=images.PNG)

    cover_url = save_album_cover('album_{}.png'.format(album_key), output_image)
    album.cover_art = cover_url
    if album.tracks:
        album.is_active = True
    album.put()

    # Reprocess the JSON output so it matches the input
    rv_dict = album.to_dict(exclude=getattr(album, 'default_exclude', None))
    rv_dict['_key'] = album.key.urlsafe()
    rv_dict['tracks'] = [{'position': k, 'track_id': v} for (k, v) in enumerate(album.tracks)]
    rv_dict['artist'] = album.artist_id.get()
    return jsonify(album=rv_dict)


'''
          Fetch Album

  METHODS: GET
  URL_PARAMS: album_key
  RETURN: JSON
  DESC: Returns the album from the db in the form of json.
'''


@album_bp.route('/<album_key>', methods=['GET'])
@auth_required()
def fetch_album(album_key):
    rv = ndb.Key(urlsafe=album_key).get()
    if not isinstance(rv, Album):
        raise NotFoundException("Unable to find the album you are looking for.")

    # Reprocess the JSON output so it matches the input
    rv_dict = rv.to_dict(exclude=getattr(rv, 'default_exclude', None))
    rv_dict['_key'] = rv.key.urlsafe()
    rv_dict['tracks'] = [{'position': k, 'track': v.get()} for (k, v) in enumerate(rv.tracks) if v.get() is not None and v.get().is_active]
    rv_dict['artist'] = rv.artist_id.get()

    return jsonify(album=rv_dict)


'''
      Fetch Album by Artist

  METHODS: GET
  URL_PARAMS: artist_key
  RETURN: JSON
  DESC: Returns the albums by a particular artist in the db.
'''


@album_bp.route('/artist/<artist_key>', methods=['GET'])
@auth_required()
def fetch_albums_by_artist(artist_key):
    return jsonify(albums=Album.query(Album.artist_id == ndb.Key(urlsafe=artist_key)).filter(Album.cover_art != None).fetch())
    #return jsonify(albums=Album.query(Album.artist_id == ndb.Key(urlsafe=artist_key)).fetch())

'''
        Remove Album by Key
    METHODS: DELETE
    URL_PARAMS: album_key
    RETURN: JSON
    DESC: Deletes an album from the datastore.
'''


@album_bp.route('/<album_key>', methods=['DELETE'])
@auth_required()
def delete_album(album_key):
    album = ndb.Key(urlsafe=album_key).get()
    if not album or not isinstance(album, Album):
        raise NotAllowedException()
    #album.key.delete()
    ndb.Key(urlsafe=album_key).delete()

    return jsonify(success="success")