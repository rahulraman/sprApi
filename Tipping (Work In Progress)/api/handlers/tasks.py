import stripe
from ..models import Album, Track,ndb
from flask import Blueprint, jsonify
from google.appengine.ext import deferred
from ..helpers.analytics import clear_weekly_plays
from ..generate_data import generate_data
tasks_bp = Blueprint('tasks', __name__)

'''
      Clear Weekly Plays

  METHODS: GET
  RETURN: JSON
  DESC: Clears weekly plays for song analytics.
'''

@tasks_bp.route('/clear_plays', methods=['GET'])
def clear_plays():
    deferred.defer(clear_weekly_plays)
    return jsonify(success="Weekly plays successfully cleared")


# @tasks_bp.route('/dummy_data', methods=['GET'])
# def delete_all_docs():
#     generate_data()
#     return jsonify(success="OK")

@tasks_bp.route('/card', methods=['GET'])
def card_generate():
    card = stripe.Token.create(card={"number": '4242424242424242',
                                     "exp_month": 12,
                                     "exp_year": 2016,
                                     "cvc": '123'})
    return jsonify(card)