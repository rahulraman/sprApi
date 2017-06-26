import logging
import re
from ..models import Artist, Album, Track, ndb
from ..errors import ValidationException


'''
         Increment Plays

   PARAMS: track_id
   VOID
   DESC: Increment the number of
 plays of the played track, album,
 and artist.
'''
def increment_plays(track_id):
    track = Track.query().filter(Track._key == ndb.Key(urlsafe=track_id)).get()
    album = Album.query().filter(Album.tracks == ndb.Key(urlsafe=track_id)).get()
    artist = Artist.query().filter(Artist._key == track.artist_id).get()

    if track:
        try:
            track.total_plays += 1
            track.weekly_plays += 1
        except AttributeError:
            track.total_plays = 1
            track.weekly_plays = 1

    if album:
        try:
            album.total_plays += 1
            album.weekly_plays += 1
        except AttributeError:
            album.total_plays = 1
            album.weekly_plays = 1

    if artist:
        try:
            artist.total_plays += 1
            artist.weekly_plays += 1
        except AttributeError:
            artist.total_plays = 1
            artist.weekly_plays = 1

    track.put()
    album.put()
    artist.put()


'''
         Album Lookup

   PARAMS: genre, num_results,
  offset
   RETURN: albums, more
   DESC: Lookup albums by there
 genre id.
'''

def album_genre_lookup(genre, num_results, offset):
    if offset:
        albums, curs, more = Album.query(Album.is_active == True).filter(Album.genre_id == int(genre)).order(-Album.average_plays).fetch_page(num_results, offset=offset)
    else:
        albums, curs, more = Album.query(Album.is_active == True).filter(Album.genre_id == int(genre)).order(-Album.average_plays).fetch_page(num_results)

    return albums, more


'''
      Generate Search Query

   PARAMS: params
   RETURN: query_string
   DESC: generates a query string
 for the search endpoint.
'''

def generate_search_query(params):
    num_params = len(params)
    query_string = "is_active = True AND "

    logging.info("PARAM KEYS: %s    PARAM VALUES: %s", params.keys(), params.values())

    for key in params.keys():
        key = key.lower()

        if key == 'keywords' or key == 'tags':
            query_string += params.get(key)
            num_params -= 1
            logging.info("KT: QUERYSTRING: %s", query_string)

            if num_params < 1:
                return query_string
            query_string += ' AND '

        if key == 'key':
            query_string += "%s = %s" %(key, params.get(key))
            num_params -= 1
            logging.info("KE: QUERTSTRING: %s", query_string)

            if num_params < 1:
                return query_string
            query_string += ' AND '
        #
        # if key == 'min_price':
        #     query_string += "price > %s" % params.get('min_price')
        #     logging.info("MIN: QUERY STRING: %s", query_string)
        #     num_params -= 1
        #
        #     if num_params < 1:
        #         return query_string
        #     query_string += ' AND '
        #
        # if key == 'max_price':
        #     query_string += "price < %s" % params.get(key)
        #     logging.info("MAX: QUERY STRING: %s", query_string)
        #     num_params -= 1
        #
        #     if num_params < 1:
        #         return query_string
        #     query_string += ' AND '

        if key == 'updated_on':
            query_string += 'updated = %s' % params.get(key)
            logging.info("UO: QUERY STRING: %s", query_string)
            num_params -= 1

            if num_params < 1:
                return query_string
            query_string += ' AND '

        if key == 'updated_before':
            query_string += 'updated < %s' % params.get(key)
            logging.info("UB: QUERY STRING: %s", query_string)
            num_params -= 1

            if num_params < 1:
                return query_string
            query_string += ' AND '

        if key == 'updated_after':
            query_string += 'updated > %s' % params.get(key)
            logging.info("UA: QUERY STRING: %s", query_string)
            num_params -= 1

            if num_params < 1:
                return query_string
            query_string += ' AND '

        if key == 'plays':
            query_string += 'total_plays >= %s' % params.get(key)
            logging.info("PLA: QUERY STRING: %s", query_string)
            num_params -= 1

            if num_params < 1:
                return query_string
            query_string += ' AND '

    raise ValidationException(description="Unable to validate your url params", payload=params)


