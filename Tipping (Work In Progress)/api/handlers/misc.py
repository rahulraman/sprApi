import time

from flask import Blueprint, jsonify

misc_bp = Blueprint('core', __name__)


@misc_bp.route('/')
def hello():
    return jsonify(status='OK 2', time=time.time())