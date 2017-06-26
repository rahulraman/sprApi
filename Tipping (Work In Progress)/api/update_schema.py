import logging
import models
import datetime
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from models import ndb
from boto.s3.connection import S3Connection

BATCH_SIZE = 2000

logs = logging.getLogger(__name__)
logs.setLevel(logging.INFO)


'''
          Update Schema

  PARAMS: album_cursor, artist_cursor, track_cursor, num_updated
  VOID
  DESC: Updates the database Schema for database migration.
'''


def UpdateSchema(album_cursor=None, artist_cursor=None, track_cursor=None, num_updated=0):
    album_query = models.Album.query()
    artist_query = models.Artist.query()
    track_query = models.Track.query()

    if album_cursor:
        album, album_curs, album_more = album_query.fetch_page(2000, start_cursor=album_cursor)
    else:
        album, album_curs, album_more = album_query.fetch_page(2000)

    if artist_cursor:
        artist, artist_curs, artist_more = artist_query.fetch_page(2000, start_cursor=artist_cursor)
    else:
        artist, artist_curs, artist_more = artist_query.fetch_page(2000)
    if track_cursor:
        track, track_curs, track_more = track_query.fetch_page(2000, start_cursor=track_cursor)
    else:
        track, track_curs, track_more = track_query.fetch_page(2000)

    to_put = 0
    conn = S3Connection('AKIAJJO6BE4JSVIVB5WQ', 'FORFPXLVheCTLBKfW52esQX8YvxdTPpV5Kp6Yn7e')
    b = conn.get_bucket('spr-tracks-source')


    for r in artist:

        if not r.is_active:
            if r.name and r.name != '' and r.name is not None and r.photo and r.photo != 'https://s3.amazonaws.com/spr-artist-images/profile.png':
                r.is_active = True
            else:
                r.is_active = False
            #to_put.append(r)

        if not r.weekly_plays or not r.total_plays:
            r.weekly_plays = 0
            r.total_plays = 0
            #to_put.append(r)
        r.put()
        to_put+=1



    for p in track:
        p.is_active = False

        if p.source_file:
            aws_file = b.get_key(key_name=p.source_file)
            if aws_file and p.title and p.artist_id:
                single_artist = ndb.Key(urlsafe=p.artist_id.urlsafe()).get()
                if single_artist and single_artist.name and single_artist.name is not None and single_artist.name != '':
                    p.artist_name = single_artist.name
                    if len(p.artist_name) > 2:
                        p.is_active = True

            #to_put.append(p)

        if not p.weekly_plays or not p.total_plays:
            p.weekly_plays = 0
            p.total_plays = 0
            #to_put.append(p)

        to_put += 1

        p.put()

    for a in album:
        if not a.release_date:
            a.release_date = datetime.datetime.utcnow()

        active = False
        if a.cover_art and a.cover_art != 'https://s3.amazonaws.com/spr-album-art/record.png':
            if a.tracks:
                active = True
                # for t in a.tracks:
                #     tr = t.get()
                #     if not tr.is_active or not tr.source_file:
                #         active = False

                to_put += 1

        a.is_active = active

        if not a.weekly_plays or not a.total_plays:
            a.weekly_plays = 0
            a.total_plays = 0

        single_artist = ndb.Key(urlsafe=a.artist_id.urlsafe()).get()
        if not single_artist or not single_artist.name or single_artist.name is None or single_artist.name == '':
            a.is_active = False
        else:
            a.artist_name = single_artist.name

        a.put()

        to_put += 1


    if to_put:

        num_updated += to_put

        logs.info('Put %d entities to Datastore for a total of %d', to_put, num_updated)

        deferred.defer(UpdateSchema, album_cursor=album_curs, artist_cursor=artist_curs,
                       track_cursor=track_curs, num_updated=num_updated)
    else:
        logs.info('UpdateSchema complete with %d updates!', num_updated)


