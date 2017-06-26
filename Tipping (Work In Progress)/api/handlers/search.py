import logging
from flask import Blueprint, jsonify, request
from ..models import Artist, Album, Track, ndb
from ..helpers.auth import auth_required
from ..helpers.misc import generate_search_query
from google.appengine.api import search

search_bp = Blueprint('search', __name__)

import logging
import json
import ast

'''
   Search the Database

   METHODS: GET
   URL_PARAMS: keywords,tags, key, min_price, max_price, updated_on, updated_before, updated_after, plays, page_size,
   offset.
   RETURN: JSON
   DESC: Search the database for a particular keyword or order.
'''


@search_bp.route('/', methods=['GET'])
@auth_required()
def search_all():
    page_size =int(request.args.get('page_size')or 30)
    offset = int(request.args.get('offset') or 0)

    index_artist = search.Index('Artist')
    index_albums = search.Index('Album')
    index_tracks = search.Index('Track')

    search_query = search.Query(query_string=generate_search_query(request.args).strip(), options=search.QueryOptions(limit=page_size, offset=offset))

    artist_results = index_artist.search(search_query)
    album_results = index_albums.search(search_query)
    track_results = index_tracks.search(search_query)

    keys = []
    for doc in artist_results:
     keys.append(next(f.value for f in doc.fields if f.name == 'key'))

    artists = []
    for key in keys:
        a = ndb.Key(urlsafe=key).get()
        if a is not None:
            artists.append(a)

    keys = []
    for doc in album_results:
        keys.append(next(f.value for f in doc.fields if f.name == 'key'))

    # TODO remove Try and except on the final production server
    albums = []
    for key in keys:
        try:
            a = ndb.Key(urlsafe=key).get()
        except BaseException:
            continue
        if a is not None:
            albums.append(a)

    keys = []
    for doc in track_results:
        keys.append(next(f.value for f in doc.fields if f.name == "key"))

    tracks = []
    for key in keys:
        a = ndb.Key(urlsafe=key).get()
        if a is not None:
            tracks.append(a)

    return jsonify(results={'artists': artists, 'albums': albums, 'tracks': tracks})

'''
   Search Artist

   METHODS: GET
   URL_PARAMS: keywords,tags, key, min_price, max_price, updated_on, updated_before, updated_after, plays, page_size,
   offset.
   RETURN: JSON
   DESC: Search the database for a particular Artist with a keyword or order.

'''


@search_bp.route('/artist', methods=['GET'])
@auth_required()
def search_artist():
    page_size = int(request.args.get('page_size')or 30)
    offset = int(request.args.get('offset') or 0)

    index_artist = search.Index('Artist')

    search_query = search.Query(query_string=generate_search_query(request.args).strip(), options=search.QueryOptions(limit=page_size, offset=offset))

    artist_results = index_artist.search(search_query)

    keys = []
    for doc in artist_results:
     keys.append(next(f.value for f in doc.fields if f.name == 'key'))

    artists = []
    for key in keys:
        a = ndb.Key(urlsafe=key).get()
        if a is not None:
            albums = Album.query(Album.artist_id == a.key).filter(Album.is_active == True).fetch()
            if albums:
                artists.append(a)

    return jsonify(artists=artists)

'''
  Search Albums

  METHODS: GET
  URL_PARAMS: keywords,tags, key, min_price, max_price, updated_on, updated_before, updated_after, plays, page_size,
  offset
  RETURN: JSON
  DESC: Search the database for a particular Albums with a keyword or order.
'''


@search_bp.route('/albums', methods=['GET'])
@auth_required()
def search_albums():
    page_size = int(request.args.get('page_size')or 30)
    offset = int(request.args.get('offset') or 0)

    index_albums = search.Index('Album')

    search_query = search.Query(query_string=generate_search_query(request.args).strip(), options=search.QueryOptions(limit=page_size, offset=offset))

    album_results = index_albums.search(search_query)

    keys = []
    for doc in album_results:
        keys.append(next(f.value for f in doc.fields if f.name == 'key'))

    # TODO remove Try and except on the final production server
    albums = []
    for key in keys:
        try:
            a = ndb.Key(urlsafe=key).get()
        except BaseException:
            continue

        if a is not None:
            albums.append(a)

    return jsonify(albums=albums)

'''
  Search Tracks

  METHODS: GET
  URL_PARAMS: keywords,tags, key, min_price, max_price, updated_on, updated_before, updated_after, plays, page_size,
  offset
  RETURN: JSON
  DESC: Search the database for a particular Tracks with a keyword or order.
'''


@search_bp.route('/tracks', methods=['GET'])
@auth_required()
def search_tracks():
    page_size = int(request.args.get('page_size')or 30)
    offset = int(request.args.get('offset') or 0)

    index_tracks = search.Index('Track')

    search_query = search.Query(query_string=generate_search_query(request.args).strip(), options=search.QueryOptions(limit=page_size, offset=offset))
    logging.log(logging.INFO, generate_search_query(request.args).strip())
    track_results = index_tracks.search(search_query)

    keys = []
    for doc in track_results:
        keys.append(next(f.value for f in doc.fields if f.name == "key"))

    tracks = []
    for key in keys:
        a = ndb.Key(urlsafe=key).get()
        if a is not None:
            album_for_track = Album.query().filter(Album.tracks == a.key).get()
            if not album_for_track or not album_for_track.is_active:
                continue
            tracks.append({"album": album_for_track, "track": a})

    return jsonify(tracks=tracks)

