import logging
from ..models import Artist, Album, Track
from google.appengine.ext import deferred
from google.appengine.ext import ndb

BATCH_SIZE = 100

logs = logging.getLogger(__name__)
logs.setLevel(logging.INFO)


######################################
#       Clear Weekly Plays           #
######################################
#   PARAMS: album_cursor,            #
# artist_cursor, track_cursor,       #
# num_updated                        #
#   VOID                             #
#   DESC: resets the weekly plays    #
# static in the database using a     #
# cursor object.                     #
######################################

def clear_weekly_plays(album_cursor=None, artist_cursor=None, track_cursor=None, num_updated=0):
    album_query = Album.query()
    artist_query = Artist.query()
    track_query = Track.query()

    if album_cursor:
        album, album_curs, album_more = album_query.fetch_page(100, start_cursor=album_cursor)
    else:
        album, album_curs, album_more = album_query.fetch_page(100)

    if artist_cursor:
        artist, artist_curs, artist_more = artist_query.fetch_page(100, start_cursor=artist_cursor)
    else:
        artist, artist_curs, artist_more = artist_query.fetch_page(100)
    if track_cursor:
        track, track_curs, track_more = track_query.fetch_page(100, start_cursor=track_cursor)
    else:
        track, track_curs, track_more = track_query.fetch_page(100)

    to_put = 0

    for p in album:
        p.weekly_plays = 0
        to_put += 1
        p.put()

    for p in artist:
        p.weekly_plays = 0
        to_put += 1
        p.put()
    for p in track:
        p.weekly_plays = 0
        to_put += 1
        p.put()
    if to_put:
        num_updated += to_put
        logs.info('Updated %d entities for analytics for a total of %d', to_put, num_updated)

        deferred.defer(clear_weekly_plays, album_cursor=album_curs, artist_cursor=artist_curs,
                       track_cursor=track_curs,num_updated=num_updated)
    else:
        logs.info('Weekly plays updated with %d entities updated ')
