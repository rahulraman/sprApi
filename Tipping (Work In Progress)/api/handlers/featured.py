import logging
from flask import Blueprint, jsonify

from ..models import Artist, Album, Track, ndb
from ..helpers.auth import auth_required

featured_bp = Blueprint('featured', __name__)


'''
           Featured

  METHODS: GET
  RETURN: JSON
  DESC: Get new_records, hot _artist, hot_tracks, hot_hip_hop,hot_electronic, hot_pop, hot_rock, and hot_classical music
   from the db queried by time or the computed property average plays.
'''


@featured_bp.route('/', methods=['GET'])
@auth_required()
def get_featured():
    new_records = Album.query(Album.is_active == True).order(-Album.created_at).fetch(limit=10)
    hot_artists = []
    artists = Artist.query().order(-Artist.average_plays).filter(Artist.is_active == True).fetch(limit=30)
    for a in artists:
        albums = Album.query(Album.artist_id == a.key).filter(Album.is_active == True).fetch()
        if albums:
            hot_artists.append(a)
        if len(hot_artists) >= 10:
            break
    hot_tracks = []
    tracks = Track.query().order(-Track.average_plays).filter(Track.is_active==True).fetch(limit=60)
    for track in tracks:
        album_for_track = Album.query().filter(Album.tracks == track._key).get()
        if not album_for_track or not album_for_track.is_active:
            continue
        if len(hot_tracks) >= 10:
            break

        hot_tracks.append({"album": album_for_track, "track": track})
    hot_hip_hop = Album.query(Album.is_active == True).filter(Album.genre_id == 7).order(-Album.average_plays).fetch(limit=10)
    hot_electronic = Album.query(Album.is_active == True).filter(Album.genre_id == 52).order(-Album.average_plays).fetch(limit=10)
    hot_pop = Album.query(Album.is_active == True).filter(Album.genre_id == 13).order(-Album.average_plays).fetch(limit=10)
    hot_rock = Album.query(Album.is_active == True).filter(Album.genre_id == 17).order(-Album.average_plays).fetch(limit=10)
    hot_classical = Album.query(Album.is_active == True).filter(Album.genre_id == 32).order(-Album.average_plays).fetch(limit=10)
    return jsonify(new_records=new_records, hot_artists=hot_artists, hot_tracks=hot_tracks, hot_hip_hop=hot_hip_hop,
                   hot_electronic=hot_electronic, hot_pop=hot_pop, hot_rock=hot_rock, hot_classical=hot_classical)







