import logging

from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from pprint import pprint
logger = logging.getLogger(__name__)


# Handles api errors to be returned in an understandable way.
def handle_api_error(error):
    code = 500
    if isinstance(error, APIException):
        code = error.status_code
    elif isinstance(error, HTTPException):
        code = error.code

    rv = dict(error=error.__class__.__name__)

    if isinstance(error, APIException) and error.description:
        rv['description'] = error.description

    if isinstance(error, APIException) and error.payload:
        rv['payload'] = error.payload

    response = jsonify(rv)
    response.status_code = code

    pprint(request)
    logger.exception(error)

    return response


# The Base Class for an API exception
class APIException(Exception):
    """ Base API exception class.
    """
    default_status = 500
    default_message = 'A server error occurred.'

    def __init__(self, description=None, status_code=None, payload=None):
        Exception.__init__(self)
        self.description = description or self.default_message
        self.status_code = status_code or self.default_status
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


# 401 Not Authorized Exception
class NotAuthorizedException(APIException):
    default_status = 401
    default_message = 'Unable to authenticate the user.'


# 403 Not Allowed Exception
class NotAllowedException(APIException):
    default_status = 403
    default_message = 'Action is not permitted.'


# 400 Validation Exception
class ValidationException(APIException):
    default_status = 400
    default_message = 'Unable to validate all request parameters.'


# 400 Image Exception
class ImageException(APIException):
    default_status = 400
    default_message = "Invalid Image Format"


# 404 Not Found Exception
class NotFoundException(APIException):
    default_status = 404
    default_message = "Unable to find the item you where looking for."


# 401 Incorrect Login Information
class AuthenticationException(APIException):
    default_status = 400
    default_message = "Unable to Authenticate user with the given credentials."


# 400 Stripe Exception
class StripeException(APIException):
    default_status = 400
    default_message = "Error with stripe."