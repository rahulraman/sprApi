import cgi
import logging
import re

from decimal import Decimal
from google.appengine.ext import ndb
from google.appengine.api import search

from flask import current_app

from .helpers.aws import generate_track_playback_url

DEFAULT_ARTIST_IMAGE = 'https://s3.amazonaws.com/spr-artist-images/profile.png'
DEFAULT_ALBUM_IMAGE = 'https://s3.amazonaws.com/spr-album-art/record.png'


# Base
class BaseModel(ndb.Model):
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def _can(cls, user, action):
        return user.is_admin or False

    def get_parent(self):
        return self.key.parent().get()

    def from_dict(self, input_dict):
        """Update model from dictionary keys."""

        for key in input_dict.keys():
            # Skip attributes that would alter the key
            if key == 'key' or key == '_key':
                continue

            if hasattr(self, key):
                setattr(self, key, input_dict[key])
    @classmethod
    def _post_delete_hook(cls, key, future):
        s = key.get()
        if hasattr(s, '_delete_hook'):
            s._delete_hook(key)


# Extensions
class DecimalProperty(ndb.IntegerProperty):
    def _validate(self, value):
        if not isinstance(value, (Decimal, float, str, unicode, int, long)):
            raise TypeError("value can't be converted to a Decimal.")

    def _to_base_type(self, value):
        return int(round(Decimal(value) * 100))

    def _from_base_type(self, value):
        return Decimal(value) / 100


# Typed URL Generator
class TypedURL(ndb.Model):
    type = ndb.StringProperty(required=True)
    url = ndb.StringProperty(required=True)


# Models
class User(BaseModel):
    default_exclude = ['auth_ids', 'credentials', 'roles']

    # Required properties
    email = ndb.StringProperty()
    email_verified = ndb.BooleanProperty(default=False)
    roles = ndb.StringProperty(repeated=True)

    # Profile properties
    name = ndb.StringProperty()

    # Credentials
    auth_ids = ndb.StringProperty(repeated=True)


# Access Token Model
class AccessToken(BaseModel):
    default_exclude = ['secret_key', 'user_id', 'platform', 'device_model']

    # Device information
    platform = ndb.StringProperty()
    device_model = ndb.StringProperty()

    access_token = ndb.StringProperty(required=True)
    secret = ndb.StringProperty(required=True)
    is_active = ndb.BooleanProperty(default=True)

    user_id = ndb.KeyProperty(kind=User, required=True)

    # TODO: Remove this once we know we've isolated the reload issue.
    def _pre_put_hook(self):
        logging.info('Attempting to save a token: ' + str(self.access_token))
        rv = AccessToken.query(AccessToken.access_token == self.access_token).get()
        logging.info('We were able to find: ' + str(rv))
        if rv:
            raise ValueError("Duplicate access token key insertion attempted. Sadface.")


# Rating Model
class Rating(BaseModel):
    """ Rating object to track track/artist ratings
    """
    poster = ndb.KeyProperty(kind=User, required=True)
    rating = ndb.IntegerProperty(required=True, choices=[1, 2, 3, 4, 5])


# Music Analytics Model
class MusicAnalytics(BaseModel):
    weekly_plays = ndb.IntegerProperty(default=0)
    total_plays = ndb.IntegerProperty(default=0)
    average_plays = ndb.ComputedProperty(lambda self: (self.weekly_plays + self.total_plays)/2)


# Artist Model
class Artist(MusicAnalytics):
    default_exclude = ['owner', 'stripe_token', 'is_active']

    name = ndb.StringProperty()
    owner = ndb.KeyProperty(kind=User, required=True)
    is_active = ndb.BooleanProperty(default=False)

    location = ndb.StringProperty()
    bio = ndb.StringProperty()

    # URL for artist photo
    photo = ndb.StringProperty()

    # Artist links
    links = ndb.StructuredProperty(TypedURL, repeated=True)

    stripe_token = ndb.StringProperty()
    customer_token = ndb.StringProperty()
    has_stripe = ndb.ComputedProperty(lambda self: self.stripe_token is not None)

    # Creates a Search Index before put.
    def _post_put_hook(self, future):
        doc = search.Document(doc_id=self.key.urlsafe(),
                              fields=[search.TextField(name='key', value=unicode(self._key.urlsafe())),
                                      search.TextField(name='name', value=self.name),
                                      search.DateField(name='created_at', value=self.created_at),
                                      search.DateField(name='updated_at', value=self.updated_at),
                                      search.TextField(name='owner', value=unicode(self.owner.urlsafe())),
                                      search.TextField(name='is_active', value=unicode(self.is_active)),
                                      search.TextField(name='location', value=self.location),
                                      search.TextField(name='bio', value=self.bio),
                                      search.TextField(name='photo', value=self.photo),
                                      search.TextField(name='links', value=unicode(self.links)),
                                      search.TextField(name='stripe_token', value=self.stripe_token),
                                      search.NumberField(name='average_plays', value=self.average_plays),
                                      search.NumberField(name='weekly_plays', value=self.weekly_plays),
                                      search.NumberField(name='total_plays', value=self.total_plays),
                                      search.TextField(name='substrings', value=tokenize(unicode(self.name) + ' ' + unicode(self.location) + ' ' + unicode(self.bio)))])
        search.Index(name=self._class_name()).put(doc)


    def _delete_hook(self,key):
        doc_index = search.Index(name='Artist')
        doc_index.delete(key.urlsafe())

# Audio File Model
class AudioFile(ndb.Model):
    """ Structured property to represent audio file URL and formats.
        The quality index is an arbitrary integer to specify the streaming quality
        of the file. Lowest is the lowest-quality stream. The client code is
        responsible for determining the appropriate choice
    """
    quality_index = ndb.IntegerProperty(required=True)
    url = ndb.StringProperty(required=True)


# Currency Value
class CurrencyValue(ndb.Model):
    """ Structured property to represent a price.
        Includes currency code and the decimal amount (stored as integer/cents).
    """

    amount = DecimalProperty(required=True)
    currency = ndb.StringProperty(required=True)


# Track Model
class Track(MusicAnalytics):
    default_exclude = ['is_active', 'source_file']

    title = ndb.StringProperty(required=True)
    artist_id = ndb.KeyProperty(kind=Artist, required=True)
    price = ndb.StructuredProperty(CurrencyValue)

    artist_name = ndb.StringProperty()

    # URL for source audio file
    source_file = ndb.StringProperty()

    playback_url = ndb.ComputedProperty(lambda self: generate_track_playback_url(self.source_file) if self.source_file else None)

    # TODO: Add flags for errors in async file processing

    explicit = ndb.BooleanProperty(default=False)

    is_active = ndb.BooleanProperty(default=False)

    # Creates a Search Index before put.
    def _post_put_hook(self, future):
        doc = search.Document(doc_id=self.key.urlsafe(),
                              fields=[search.TextField(name='key', value=unicode(self._key.urlsafe())),
                                      search.DateField(name='created_at', value=self.created_at),
                                      search.DateField(name='updated_at', value=self.updated_at),
                                      search.TextField(name='title', value=self.title),
                                      search.TextField(name='artist_name',value=unicode(self.artist_name)),
                                      search.TextField(name='artist_id', value=unicode(self.artist_id.urlsafe())),
                                      search.TextField(name='source_file', value=self.source_file),
                                      search.TextField(name='explicit', value=unicode(self.explicit)),
                                      search.TextField(name='is_active', value=unicode(self.is_active)),
                                      search.NumberField(name='average_plays', value=self.average_plays),
                                      search.NumberField(name='weekly_plays', value=self.weekly_plays),
                                      search.NumberField(name='total_plays', value=self.total_plays),
                                      search.TextField(name='substrings', value=tokenize(unicode(self.title) + ' ' + unicode(self.artist_name)))])
        search.Index(name=self._class_name()).put(doc)


    def _delete_hook(self,key):
        logging.log(logging.info(),"Runnung")
        doc_index = search.Index(name='Track')
        doc_index.delete(key.urlsafe())


# Album Model
class Album(MusicAnalytics):
    default_exclude = ['is_active']

    title = ndb.StringProperty(required=True)
    artist_id = ndb.KeyProperty(kind=Artist)
    artist_name = ndb.StringProperty()
    tracks = ndb.KeyProperty(kind=Track, repeated=True)
    is_active = ndb.BooleanProperty(default=False)

    price = ndb.StructuredProperty(CurrencyValue)

    # URL for cover art
    cover_art = ndb.StringProperty()

    description = ndb.StringProperty()
    release_date = ndb.DateProperty()
    genre_id = ndb.IntegerProperty()

    # Creates a Search Index before put.
    def _post_put_hook(self, future):
        doc = search.Document(doc_id=self.key.urlsafe(),
                              fields=[search.TextField(name='key', value=unicode(self._key.urlsafe())),
                                      search.DateField(name='created_at', value=self.created_at),
                                      search.DateField(name='updated_at', value=self.updated_at),
                                      search.TextField(name='title', value=self.title),
                                      search.TextField(name='artist_id', value=unicode(self.artist_id.urlsafe())),
                                      search.TextField(name='artist_name',value=unicode(self.artist_name)),
                                      search.TextField(name='tracks', value=unicode(self.tracks)),
                                      search.TextField(name='is_active', value=unicode(self.is_active)),
                                      search.TextField(name='cover_art', value=self.cover_art),
                                      search.TextField(name='description', value=self.description),
                                      search.DateField(name='release_date', value=self.release_date),
                                      search.NumberField(name='genre_id', value=int(self.genre_id if self.genre_id else 7)),
                                      search.NumberField(name='average_plays', value=self.average_plays),
                                      search.NumberField(name='weekly_plays', value=self.weekly_plays),
                                      search.NumberField(name='total_plays', value=self.total_plays),
                                      search.TextField(name='substrings', value=tokenize(unicode(self.title) + ' ' + unicode(self.description) + ' ' + unicode(self.artist_name)))])
        search.Index(name=self._class_name()).put(doc)

    def _delete_hook(self,key):
        doc_index = search.Index(name='Album')
        doc_index.delete(key.urlsafe())


# Comment Model
class Comment(BaseModel):
    default_exclude = ['flags', 'flagged_by']

    def _validate_comment(self, prop, value):
        """Ensure comment isn't too long and does not have any illicit HTML. """

        max_len = current_app.config['COMMENT_MAX_LENGTH']
        if len(value) > max_len:
            rv = value[:max_len]
        else:
            rv = value

        return cgi.escape(rv)

    poster = ndb.KeyProperty(kind=User, required=True)
    comment = ndb.StringProperty(required=True, validator=_validate_comment)

    flagged_by = ndb.KeyProperty(kind=User, repeated=True)
    flags = ndb.ComputedProperty(lambda self: len(self.flagged_by))


# Purchase Model
class Purchase(BaseModel):
    pass


# Play Model
class Play(BaseModel):
    """ Record each play of a track for analytics.

    TODO: Should consider using a _post_put_hook for that one day.
    """
    user = ndb.KeyProperty(kind=User, required=True)
    track = ndb.KeyProperty(kind=Track, required=True)


# Flag Model
class Flag(BaseModel):
    flagger = ndb.KeyProperty(kind=User, required=True)
    album = ndb.KeyProperty(kind=Album)
    artist = ndb.KeyProperty(kind=Artist)
    reason = ndb.StringProperty()


def tokenize(string_to_tokenize):
    rv = []
    for t in set(re.sub('[^a-z ]', '', string_to_tokenize.lower()).split(' ')):
        rv.extend([t[:v] for v in range(3, len(t) + 1)] if len(t) > 3 else [t])

    return ' '.join(set(rv))
