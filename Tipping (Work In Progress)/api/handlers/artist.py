import stripe
import logging
from flask import Blueprint, jsonify, g, request
from google.appengine.api import images
from google.appengine.ext import ndb

from ..models import Artist, Album, TypedURL,Track
from ..helpers.auth import auth_required
from ..helpers.aws import save_artist_photo
from ..errors import APIException, NotAllowedException, ImageException, StripeException, NotFoundException
from ..utils import validate_params

artist_bp = Blueprint('artist', __name__)


'''
          Create Artist

  METHODS: POST
  PARAMS: name, location, bio,
  OPTIONAL: links, (stripe_token)
  RETURN: JSON
  DESC: Creates an Artist object and puts that object in the db.
'''


@artist_bp.route('/', methods=['POST'])
@auth_required()
def create_artist():
    validate_params(['name', 'location', 'bio'])
    name = request.json.get('name')
    location = request.json.get('location')
    bio = request.json.get('bio')

    if request.json.get('links'):
        links = [TypedURL(type=l.get('type'), url=l.get('url')) for l in request.json.get('links')]
    else:
        links = []

    stripe_token = request.json.get('stripe_token')

    # TODO: Add remaining, necessary fields for Stripe tokens

    new_artist = Artist(owner=g.user.key,
                        name=name,
                        location=location,
                        bio=bio,
                        links=links,
                        stripe_token=stripe_token)
    new_artist.put()

    return jsonify(artist=new_artist)


'''
          Update Artist

  METHODS: PUT
  PARAMS: name, location, bio,
  URL_PARAMS: artist_key
  OPTIONAL: links, (stripe_token)
  RETURN: JSON
  DESC: Creates an Artist object and puts that object in the db.
'''


@artist_bp.route('/<artist_key>', methods=['PUT'])
@auth_required()
def update_artist(artist_key):
    validate_params(['name', 'location', 'bio'])
    artist = ndb.Key(urlsafe=artist_key).get()
    if not artist or not isinstance(artist, Artist):
        raise NotAllowedException()

    updated_fields = dict()
    updated_fields['name'] = request.json.get('name')
    updated_fields['location'] = request.json.get('location')
    updated_fields['bio'] = request.json.get('bio')

    if request.json.get('links'):
        updated_fields['links'] = [TypedURL(type=l.get('type'), url=l.get('url')) for l in request.json.get('links')]

    updated_fields['stripe_token'] = request.json.get('stripe_token')

    artist.from_dict(updated_fields)
    artist.put()

    albums = Album.query(Album.is_active==True).filter(Album.artist_id == artist.key).fetch()
    tracks = Track.query().filter(Track.artist_id == artist.key).fetch()
    if albums:
        for a in albums:
            a.artist_name = artist.name
            a.put()
    if tracks:
        for t in tracks:
            t.artist_name = artist.name
            t.put()

    return jsonify(artist=artist)


'''
       Post Artist Photo

  METHODS: POST
  PARAMS: photo
  URL_PARAMS: artist_key
  RETURN: JSON
  DESC: A Multi-part request that creates a url for an image and adds that url to an artist.
'''


@artist_bp.route('/<artist_key>/photo', methods=['POST'])
@auth_required()
def update_artist_photo(artist_key):
    artist = ndb.Key(urlsafe=artist_key).get()
    if not artist or not isinstance(artist, Artist):
        raise NotAllowedException()

    # Process the image
    uploaded_image = request.files.get('photo')
    if not uploaded_image:
        raise ImageException(description='Invalid image. Unable to get the image form the request in '
                                         'the correct format.')

    image = images.Image(uploaded_image.read())

    if image.height < 1024 or image.width < 1024:
        raise ImageException(description='Invalid image size. The image uploaded was smaller then 1024 X 1024')

    # Scale to ensure the smallest dimension is 1024px
    image.resize(width=1024, height=1024, crop_to_fit=True)
    output_image = image.execute_transforms(output_encoding=images.PNG)

    photo_url = save_artist_photo('artist_{}.png'.format(artist_key), output_image)
    artist.photo = photo_url
    artist.is_active = True
    artist.put()

    return jsonify(artist=artist)


'''
          Fetch Artist

  METHODS: GET
  URL_PARAMS: artist_key
  RETURN: JSON
  DESC: Returns the artist from the db in the form of json.
'''


@artist_bp.route('/<artist_key>', methods=['GET'])
@auth_required()
def fetch_artist(artist_key):
    rv = ndb.Key(urlsafe=artist_key).get()
    return jsonify(artist=rv if isinstance(rv, Artist) else None)


'''
      Fetch Artist Page

  METHODS: GET
  URL_PARAMS: artist_key
  RETURN: JSON
  DESC: Returns the artist, the artist's albums, and total tracks
'''


@artist_bp.route('/<artist_key>/page', methods=['GET'])
@auth_required()
def fetch_artist_page(artist_key):
    artist = ndb.Key(urlsafe=artist_key).get()
    albums = Album.query(Album.is_active == True).filter(Album.artist_id == ndb.Key(urlsafe=artist_key)).fetch()
    total_tracks = 0
    for a in albums:
        total_tracks += len(a.tracks)
    return jsonify(artist=artist, albums=albums, total_tracks=total_tracks)


'''
             List Artist

  METHODS: GET
  RETURN: JSON
  DESC: Lists the artist for a user.
'''


@artist_bp.route('/list', methods=['GET'])
@auth_required()
def fetch_artists_for_user():
    return jsonify(artists=Artist.query(Artist.owner == g.user.key).fetch())

'''
Adds a stripe account to an artist.
'''


@artist_bp.route('/<artist_id>/stripe', methods=['POST'])
@auth_required()
def add_stripe_account(artist_id):
    validate_params(['account_token'])
    artist = ndb.Key(urlsafe=artist_id).get()
    if not artist or not isinstance(artist, Artist):
        raise NotAllowedException()
    try:
        account = stripe.Account.retrieve(request.json.get('account_token'))

    except stripe.error.StripeError as e:
        raise StripeException(e)
    artist.stripe_token = unicode(account.stripe_id)
    artist.put()
    logging.log(logging.INFO, artist.stripe_token)

    return jsonify(artist=artist, account=account)


'''
Adds a card to a customer, otherwise creates a customer then adds a card.
'''


@artist_bp.route('/<artist_id>/cards', methods=['POST'])
@auth_required()
def add_card(artist_id):
    validate_params(['card_token'])
    artist = ndb.Key(urlsafe=artist_id).get()
    if not artist or not isinstance(artist, Artist) or artist.owner.get is not g.user:
        raise NotAllowedException()
    customer = None
    try:
        if artist.customer_token and artist.customer_token is not None:
            customer = stripe.Customer.retrieve(artist.customer_token)
            card = customer.sources.create(source=request.json.get('card_token'))
            customer.refresh()
        else:
            customer = stripe.Customer.create(metadata={'artist_name':artist.name,'artist_id':artist.key.urlsafe()},
                                              source=request.json.get('card_token'))
            artist.customer_token = customer.stripe_id
            artist.put()
    except stripe.error.StripeError as e:
        logging.log(logging.INFO, e)
        raise StripeException(e)

    return jsonify(artist=artist, customer=customer)

'''
Gets a list of cards from a customer.
'''


@artist_bp.route('/<artist_id>/cards', methods=['GET'])
@auth_required()
def get_customer_cards(artist_id):
    artist = ndb.Key(urlsafe=artist_id).get()
    if not artist or not isinstance(artist, Artist) or artist.owner.get() is not g.user:
        raise NotAllowedException()
    customer = None
    try:
        customer = stripe.Customer.retrieve(artist.customer_token) if artist.customer_token else []
    except stripe.error.StripeError as e:
        raise StripeException(e)
    return jsonify(cards=customer.sources.all(object='card') if customer else [])

'''
Tips an artist using stripe.
'''


@artist_bp.route('/<artist_id>/tip', methods=['POST'])
@auth_required()
def make_payment(artist_id):
    validate_params(['amount', 'from_artist', 'card_token'])
    receiving_artist = ndb.Key(urlsafe=artist_id).get()
    sending_artist = ndb.Key(urlsafe=request.json.get('from_artist')).get()
    if not receiving_artist or not isinstance(receiving_artist, Artist) or sending_artist.owner.get() is not g.user:
        raise NotAllowedException()
    total = request.json.get('amount')
    stripe_fee = 30 + total*.029
    cut = max((total*.25)-stripe_fee, 50 - stripe_fee)
    charge = None
    if sending_artist.customer_token is None:
        raise StripeException("You must add a card to tip an artist.")
    if receiving_artist.stripe_token is None:
        logging.log(logging.INFO, receiving_artist.stripe_token)
        raise StripeException("This artist does not have tips enabled.")
    try:
        charge = stripe.Charge.create(amount=str(total), currency="usd",
                                      destination=receiving_artist.stripe_token, customer=sending_artist.customer_token,
                                      source=request.json.get('card_token'), application_fee=int(cut))
    except stripe.error.StripeError as e:
        logging.log(logging.INFO, e)
        raise StripeException(e)

    return jsonify(charge=charge)

'''
Deletes stripe cards from a stripe customer.
'''


@artist_bp.route('/<artist_id>/cards/delete', methods=['POST'])
@auth_required()
def delete_card(artist_id):
    validate_params(['card'])
    artist = ndb.Key(urlsafe=artist_id).get()
    if not artist.customer_token:
        raise NotFoundException("A customer is not connected to your artist.")
    customer = stripe.Customer.retrieve(artist.customer_token)
    if not customer:
        raise StripeException("Not able to find customer with your artist ID.")

    customer.sources.retrieve(request.json.get('card')).delete()
    customer.refresh()

    return jsonify(cards=customer.sources.all(object='card'))