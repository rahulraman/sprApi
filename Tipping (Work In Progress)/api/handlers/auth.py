import logging

from flask import Blueprint, request, current_app, abort, jsonify, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from ..models import User, AccessToken, Artist
from ..helpers.auth import CredentialManager, CredentialVerifier, auth_required
from ..errors import APIException, AuthenticationException
from ..utils import send_mandrill_email, random_string

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


'''
   Register User

   METHODS: POST
   PARAMS: credentials
   URL_PARAMS: provider
   RETURN: JSON
   DESC: Creates a new user using validation from a provider
'''


@auth_bp.route('/register/<provider>', methods=['POST'])
def create_user(provider):

    # TODO: Validation (required properties, etc.)

    # Check to see if this user already exists
    verifier = CredentialVerifier(provider, request.json.get('credentials'))
    user = verifier.get_user()

    if user:
        raise AuthenticationException('Cannot create user, user already exists.', 400)

    # Create the new user
    user = User()

    # Extract the email address
    user.email = request.json.get('email')

    manager = CredentialManager(provider, request.json.get('credentials'))
    manager.attach(user)

    # Set the rest of the user profile information
    user.first_name = request.json.get('first_name')
    user.last_name = request.json.get('last_name')

    user_key = user.put()
    if user_key is None:
        raise AuthenticationException('Error adding user to database.')

    # Create a verification token

    # token_generator = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

    # Generate a new verification request emails

    # context = {'verification': token_generator.dumps(user.email)}
    # send_mandrill_email(user.email, 'email-verification', context)

    # Return a new access token
    token = AccessToken(user_id=user_key,
                        platform=request.json.get('platform'),
                        device_model=request.json.get('device_model'),
                        access_token=random_string(),
                        secret=random_string())
    token.put()

    return jsonify(user=user,
                   access_token=token.to_dict(include=['access_token', 'secret']))


'''
  Verify User

  METHODS: POST
  PARAMS: credentials
  URL_PARAMS: verification
  RETURN: JSON
  DESC: Verifies a user's email
'''


@auth_bp.route('/verify/<verification>', methods=['POST'])
def verify_email(verification):

    # Token generator to verify
    token_generator = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

    # Determine we have a valid request
    try:
        user_email = token_generator.loads(verification, max_age=current_app.config['VERIFICATION_LIFETIME'])
        found = User.query(User.email == user_email).get()
        if not found:
            raise AuthenticationException('No valid user for this verification code.', 404)

    except (BadSignature, SignatureExpired):
        raise AuthenticationException('No valid user for this verification code.', 404)

    # Finally, mark as verified and save
    found.email_verified = True
    found.roles.append('verified')
    found.put()

    # Return our new user
    return jsonify(user_id=found.key.urlsafe(),
                   user=found.to_dict(exclude=['auth_ids', 'credentials']))


'''
  Login User

  METHODS: POST
  PARAMS: credentials, platform device
  URL_PARAMS: provider
  RETURN: JSON
  DESC: Logs in a user and creates an access token for that user.
'''


@auth_bp.route('/login/<provider>', methods=['POST'])
def login(provider):

    verifier = CredentialVerifier(provider, request.json.get('credentials'))
    user = verifier.get_user()

    if not user.auth_ids:
        manager = CredentialManager(provider, request.json.get('credentials'))
        manager.attach(user)

        user.put()

    artist = Artist.query(Artist.owner == user.key).get()

    if not artist:
        artist = Artist(owner=user.key, is_active=True, name=user.name)
        artist.put()

    # Create a device so we have keys
    token = AccessToken(user_id=user.key,
                        platform=request.json.get('platform'),
                        device_model=request.json.get('device_model'),
                        access_token=random_string(),
                        secret=random_string())
    token.put()

    return jsonify(user=user,
                   artist=artist,
                   access_token=token.to_dict(include=['access_token', 'secret']))


'''
  Get Info
  METHODS: GET
  RETURN: JSON
  DESC: Get your user info
'''


@auth_bp.route('/me')
@auth_required()
def get_me():
    return jsonify(user=g.user, artist=Artist.query(Artist.owner == g.user.key).get())
