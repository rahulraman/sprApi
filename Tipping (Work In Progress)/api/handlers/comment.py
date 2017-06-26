from flask import Blueprint, jsonify, g, request
from google.appengine.ext import ndb

from ..models import User, Comment
from ..helpers.auth import auth_required
from ..errors import APIException
from ..utils import validate_params
comment_bp = Blueprint('comment', __name__)


'''
  Post a Comment

  METHODS: POST
  PARAMS: comment, entity_key
  RETURN: JSON
  DESC: Post a comment to an artist with a particular entity key.
'''


@comment_bp.route('/', methods=['POST'])
@auth_required()
def post_comment():
    """Post a comment on an entity."""
    validate_params('comment')
    # Get the entity to comment
    entity = ndb.Key(urlsafe=request.json['entity_key']).get()

    # Confirm this is an Artist and it belongs to the current user
    if not entity:
        raise APIException('Invalid artist_key.')

    # Create the new, empty album and return
    comment = Comment(parent=entity.key,
                      poster=g.user.key,
                      comment=request.json['comment'])
    comment.put()

    return jsonify(comment)


'''
  Flag a Comment

  METHODS: POST
  PARAMS: comment_key
  URL_PARAMS: comment_key
  RETURN: JSON
  DESC: Flag a comment with a particular key.
'''


@comment_bp.route('/<comment_key>/flag', methods=['POST'])
@auth_required()
def flag_comment(comment_key):
    """Flag a comment. """

    # Get the comment associated with the input key
    comment = ndb.Key(urlsafe=comment_key).get()

    # Confirm this is a comment
    if not isinstance(comment, Comment):
        raise APIException('Invalid comment.')

    # Confirm the user has not already flagged this comment
    if g.user.key in comment.flagged_by:
        raise APIException('User has already flagged this comment.')

    # Update the album and return it
    comment.flagged_by.append(g.user.key)
    comment.put()

    return jsonify(comment)


'''
   Comments from an Entity

  METHODS: GET
  URL_PARAMS: entity_key
  RETURN: JSON
  DESC: Get the comments from an entity_key.
'''


@comment_bp.route('/entity/<entity_key>', methods=['GET'])
@auth_required()
def fetch_album(entity_key):
    """Fetch comments from an entity key."""

    parent_entity = ndb.Key(urlsafe=entity_key)
    comments = Comment.query(ancestor=parent_entity).fetch()
    return jsonify(comments=comments)