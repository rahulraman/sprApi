import random
from models import User, Album, Artist, Track,CurrencyValue
from faker import Faker
from datetime import datetime

genres = [7, 52, 13, 17, 32]
image_sets = ["abstract","animals","business","cats","city","food","night","life","fashion",
              "people","nature","sports"]

song_set = ["ag9zfnNwci1yZWV2b2x2ZWRyEgsSBVRyYWNrGICAgICQ3Z4JDA.mp3","ag9zfnNwci1yZWV2b2x2ZWRyEgsSBVRyYWNrGICAgICFwo4LDA.mp3",
            "ag9zfnNwci1yZWV2b2x2ZWRyEgsSBVRyYWNrGICAgID-oJYLDA.mp3"]


# A method to generate dummy data TODO remove in production
def generate_data():
    faker = Faker()

    for i in range(0, 24):
        name = faker.name()
        u = User(name=name)
        u.put()
        full = faker.lorem()
        firstbio, secounddis = full[:len(full)/2], full[len(full)/2:]
        a = Artist(name=name, owner=u._key, is_active=True, location=faker.full_address(), bio=firstbio)
        a.put()

        cover_art="http://lorempixel.com/1024/1024/{}".format(random.choice(image_sets))

        track_list=[]
        for i in range(0, 12):
            t = Track(title=faker.name(), artist_id=a._key, artist_name=a.name, source_file=random.choice(song_set),explicit=False, is_active=True,
                      price=CurrencyValue(amount=0, currency="USD"))
            t.put()
            track_list.append(t._key)

        alb = Album(title=faker.name(), artist_name=a.name, artist_id=a._key, tracks=track_list,
                    cover_art=cover_art,
                    description=secounddis, release_date=datetime.utcnow(), genre_id=random.choice(genres),
                    price=CurrencyValue(amount=0, currency="USD"), is_active=True)

        alb.put()
