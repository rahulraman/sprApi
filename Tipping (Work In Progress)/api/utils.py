import hashlib
import base64
import random
import calendar

from datetime import datetime, date
from decimal import Decimal

from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from flask.json import JSONEncoder
from flask import current_app, json, request

from .errors import APIException, ValidationException


# Random string generator.
def random_string():
    return base64.urlsafe_b64encode(hashlib.sha256(str(random.getrandbits(1024))).digest()).strip('=')


# Sends a Mandrill email
def send_mandrill_email(recipient, template_name, merge_vars):
    mandrill_key = current_app.config['MANDRILL_KEY']
    mandrill_url = 'https://mandrillapp.com/api/1.0/messages/send-template.json'

    message = {
        'to': [],
        'global_merge_vars': []
    }

    message['to'].append({'email': recipient})

    for k, v in merge_vars.iteritems():
        message['global_merge_vars'].append(
            {'name': k, 'content': v}
        )

    full_request = {
        'key': mandrill_key,
        'template_name': template_name,
        'template_content': [],
        'message': message,
        'async': True
    }

    content = urlfetch.fetch(mandrill_url, method=urlfetch.POST,
                             headers={'Content-Type': 'application/json'}, payload=json.dumps(full_request))

    if content.status_code != 200:
        raise APIException('Unable to send verification email.')

    return content.status_code == 200


# The Custom Json Encoder
class CustomJSONEncoder(JSONEncoder):

    def default(self, obj):
        try:
            # Expanded model from ndb.Model
            if isinstance(obj, ndb.Model):
                temp = obj.to_dict(exclude=getattr(obj, 'default_exclude', None))
                if hasattr(obj,'artist_id'):
                    temp['artist'] = obj.artist_id.get()
                temp['_key'] = obj.key.urlsafe()
                return temp

            # UNIX timestamps from datetimes
            if isinstance(obj, datetime):
                if obj.utcoffset() is not None:
                    obj = obj - obj.utcoffset()

                seconds = int(calendar.timegm(obj.timetuple()))
                return seconds

            # UNIX timestamps from date
            if isinstance(obj, date):
                seconds = int(calendar.timegm(obj.timetuple()))
                return seconds

            # URL-safe keys from ndb.Key
            if isinstance(obj, ndb.Key):
                return obj.urlsafe()

            # Decimal values to display as float
            if isinstance(obj, Decimal):
                return float(obj)

            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


# Validates Url Parameters
def validate_params(valid_params):
    not_in_request = []

    for param in valid_params:
        if request.json.get(param) is None:
            not_in_request.append(param)
    if not_in_request:
        raise ValidationException(payload=not_in_request)
    else:
        return


