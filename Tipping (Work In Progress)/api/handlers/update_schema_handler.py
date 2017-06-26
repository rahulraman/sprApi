from flask import Blueprint, jsonify, request
from google.appengine.ext import deferred
from ..update_schema import UpdateSchema
from ..models import Artist, Album

update_schema_bp = Blueprint('update_schema', __name__)


'''
  Schema Handler

  METHODS: GET
  RETURN: JSON
  DESC: The handler used to migrate the database
'''

@update_schema_bp.route('/', methods=['GET'])
def update_handler():
    deferred.defer(UpdateSchema)
    return jsonify(success='Schema migration successfully initiated')
