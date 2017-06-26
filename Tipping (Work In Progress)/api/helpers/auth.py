import urllib
import logging
import tweepy

from functools import wraps
from google.appengine.api import urlfetch
from flask import request, g, current_app, json

from ..models import User, AccessToken
from ..errors import APIException, NotAuthorizedException,AuthenticationException

logger = logging.getLogger(__name__)


# Authentication required
def auth_required(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            auth_header = request.headers.get('Authorization', None)

            if not auth_header:
                raise AuthenticationException('Malformed authentication information.', 400)

            # Parse the auth header
            (auth_type, auth_string) = auth_header.split(' ')

            if auth_type == 'Token':
                access_key = auth_string
            else:
                raise AuthenticationException('Malformed authentication information.', 400)

            # Confirm a device exists for this key
            token = AccessToken.query(AccessToken.access_token == access_key).get()
            if not token:
                raise AuthenticationException('Incorrect authentication information.', 403)

            # We have a user, check permissions
            candidate = token.user_id.get()
            for p in roles:
                if p not in candidate.roles:
                    raise NotAuthorizedException()

            g.user = candidate

            return f(*args, **kwargs)
        return wrapped
    return wrapper


# Credential creation from various sources
class CredentialManager(object):

    def __init__(self, provider, credentials):
        self.provider = provider
        self.credentials = credentials

    def attach(self, user):

        if self.provider == 'facebook':
            auth_string = self._facebook()
        elif self.provider == 'twitter':
            auth_string = self._twitter()
        else:
            raise AuthenticationException('Invalid authentication provider.')

        # Ensure there isn't already a credential for this ID on this user
        if auth_string in user.auth_ids:
            raise AuthenticationException('Credential already exists.')

        # Add the credentials
        user.auth_ids.append(auth_string)

        user.put()

    def _auth_string(self, identifier):
        return '#'.join((self.provider, identifier))

    def _facebook(self):

        # Get the access token supplied
        user_token = self.credentials.get('access_token')
        if not user_token:
            raise AuthenticationException('Invalid request format.', 400)

        # Get the Facebook user ID associated with the token
        query_parameters = {
            'input_token': user_token,
            'access_token': current_app.config.get('FACEBOOK_ACCESS_TOKEN')
        }

        facebook_url = 'https://graph.facebook.com/debug_token?{}'.format(urllib.urlencode(query_parameters))
        response = urlfetch.fetch(facebook_url)

        if response.status_code != 200:
            raise AuthenticationException('Unable to verify credentials with remote server.', 500)

        # Parse the response and confirm it is valid
        response_content = json.loads(response.content).get('data')
        if not response_content or unicode(response_content['app_id']) != current_app.config['FACEBOOK_APP_ID'] \
                or not response_content.get('user_id') or not response_content.get('is_valid'):
            raise AuthenticationException('Unable to verify credentials.', 401)

        # Save the user
        auth_string = self._auth_string(unicode(response_content.get('user_id')))

        return auth_string

    def _twitter(self):

        # Get the access token supplied
        oauth_token = self.credentials.get('oauth_token')
        oauth_token_secret = self.credentials.get('oauth_token_secret')
        if not oauth_token or not oauth_token_secret:
            raise AuthenticationException('Invalid request format.', 400)

        auth = tweepy.OAuthHandler(current_app.config['TWITTER_CONSUMER_KEY'], current_app.config['TWITTER_CONSUMER_SECRET'])
        auth.set_access_token(oauth_token, oauth_token_secret)

        api = tweepy.API(auth)
        user = api.verify_credentials()

        if not user:
            raise AuthenticationException('Unable to verify credentials with remote server.', 500)

        # Save the user
        return self._auth_string(unicode(user.id_str))


# Access verification methods
class CredentialVerifier(object):

    def __init__(self, provider, test_credentials):
        self.provider = provider
        self.test_credentials = test_credentials

    def get_user(self):

        if self.provider == 'facebook':
            return self._facebook()
        elif self.provider == 'twitter':
            return self._twitter()
        else:
            return None

    def _auth_string(self, identifier):
        return '#'.join((self.provider, identifier))

    # Provider methods

    def _facebook(self):

        # Get the access token supplied
        user_token = self.test_credentials.get('access_token')
        if not user_token:
            raise AuthenticationException('Invalid request format.', 400)

        # Get the Facebook user ID associated with the token
        query_parameters = {
            'input_token': user_token,
            'access_token': current_app.config.get('FACEBOOK_ACCESS_TOKEN')
        }

       // facebook_url = 'https://graph.facebook.com/debug_token?{}'.format(urllib.urlencode(query_parameters))
		
		facebook_url ="https://graph.facebook.com/v2.9/me?fields=id,name,email&access_token=".user_token
		
        response = urlfetch.fetch(facebook_url)

        if response.status_code != 200:
            raise AuthenticationException('Unable to verify credentials with remote server.', 401)

        # Parse the response and confirm it is valid
        response_content = json.loads(response.content).get('data')
        if not response_content or unicode(response_content['app_id']) != current_app.config['FACEBOOK_APP_ID'] \
                or not response_content.get('user_id') or not response_content.get('is_valid'):
            raise AuthenticationException('Unable to verify credentials with remote server.', 401)

        # Attempt to find a user matching the token's ID
        auth_string = self._auth_string(unicode(response_content.get('user_id')))
        user = User.query(User.auth_ids == auth_string).get()

        if user and not user.name:
            user.name = 'Facebook User'
            user.put()

        if not user:
            user = User(name='Facebook User')

        return user

    def _twitter(self):
        # Get the access token supplied
        oauth_token = self.test_credentials.get('oauth_token')
        oauth_token_secret = self.test_credentials.get('oauth_token_secret')
        if not oauth_token or not oauth_token_secret:
            raise AuthenticationException('Invalid request format.', 400)

        auth = tweepy.OAuthHandler(current_app.config['TWITTER_CONSUMER_KEY'], current_app.config['TWITTER_CONSUMER_SECRET'])
        auth.set_access_token(oauth_token, oauth_token_secret)

        api = tweepy.API(auth)
        user = api.verify_credentials()

        if not user:
            raise AuthenticationException('Unable to verify credentials with remote server.', 500)

        # Save the user
        auth_string = self._auth_string(unicode(user.id_str))

        stored_user = User.query(User.auth_ids == auth_string).get()

        if not stored_user:
            return User(name=user.name)

        if stored_user and not stored_user.name:
            stored_user.name = user.name
            stored_user.put()

        return stored_user
