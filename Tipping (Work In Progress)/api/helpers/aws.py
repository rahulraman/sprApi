import logging

from boto.s3.connection import S3Connection
from flask import current_app

logger = logging.getLogger(__name__)

AWS_ACCESS_KEY = 'AKIAJJO6BE4JSVIVB5WQ'
AWS_SECRET_KEY = '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'
SOURCE_TRACK_S3_BUCKET = 'spr-tracks-source'
ARTIST_PHOTO_S3_BUCKET = 'spr-artist-images'
ALBUM_COVER_S3_BUCKET = 'spr-album-art'

'''
  Generate Track Upload URl

  PARAMS: filename
  RETURN: url
  DESC: generates the upload url for a track from its s3 url.
'''


def generate_track_upload_url(filename):
    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    return conn.generate_url(expires_in=3600,
                             method='PUT',
                             bucket=SOURCE_TRACK_S3_BUCKET,
                             key=filename,
                             headers={'Content-type': 'application/octet-stream'})


'''
  Generate Track Playback URl

  PARAMS: filename
  RETURN: url
  DESC: generates the upload url for a track from its s3 url.
'''


def generate_track_playback_url(filename):
    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    return conn.generate_url(expires_in=604800,
                             method='GET',
                             bucket=SOURCE_TRACK_S3_BUCKET,
                             key=filename)


'''
  Save Artist Photo

  PARAMS: filename, photo
  RETURN: url
  DESC: generates the url for an artist photo in s3.
'''


def save_artist_photo(filename, photo):
    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    b = conn.get_bucket(ARTIST_PHOTO_S3_BUCKET)
    created_object = b.new_key(filename)
    created_object.set_contents_from_string(photo)
    created_object.make_public()

    return created_object.generate_url(0, query_auth=False)


'''
  Save Album Cover

  PARAMS: filename, cover
  RETURN: url
  DESC: generates the url for an album cover in s3.
'''


def save_album_cover(filename, cover):
    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    b = conn.get_bucket(ALBUM_COVER_S3_BUCKET)
    created_object = b.new_key(filename)
    created_object.set_contents_from_string(cover)
    created_object.make_public()

    return created_object.generate_url(0, query_auth=False)