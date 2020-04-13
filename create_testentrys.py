from datetime import datetime, timedelta
from random import choice, randint

from transporte import create_app, db
from transporte.models import License, Transport, User, Vehicle

app = create_app()
app.app_context().push()

roles = ["helpdesk", "user"]


if User.query.filter(User.login == "test@psy.rocks").first() is None:
    db.session.add(User(login="test@psy.rocks", role="admin"))
if User.query.filter(User.login == "user1@psy.rocks").first() is None:
    db.session.add(User(login="user1@psy.rocks", role="user"))
if User.query.filter(User.login == "user2@psy.rocks").first() is None:
    db.session.add(User(login="user2@psy.rocks", role="user"))
if User.query.filter(User.login == "help@psy.rocks").first() is None:
    db.session.add(User(login="help@psy.rocks", role="helpdesk"))
db.session.commit()

users = User.query.all()

if License.query.filter(License.name == "C1").first() is None:
    db.session.add(License(name="C1"))
if License.query.filter(License.name == "C1E").first() is None:
    db.session.add(License(name="C1E"))
if License.query.filter(License.name == "CE").first() is None:
    db.session.add(License(name="CE"))
if License.query.filter(License.name == "B*").first() is None:
    db.session.add(License(name="B*"))
db.session.commit()

licenses = License.query.all()

if Vehicle.query.filter(Vehicle.name == "9Sitzer").first() is None:
    db.session.add(
        Vehicle(
            name="9Sitzer",
            required_license_id=License.query.filter(License.name == "B*").first().id,
            rented_from=datetime.now() - timedelta(days=1),
            rented_until=datetime.now() + timedelta(days=5),
        )
    )
if Vehicle.query.filter(Vehicle.name == "7.5 A").first() is None:
    db.session.add(
        Vehicle(
            name="7.5 A",
            required_license_id=License.query.filter(License.name == "C1").first().id,
            rented_from=datetime.now() - timedelta(days=1),
            rented_until=datetime.now() + timedelta(days=5),
        )
    )
if Vehicle.query.filter(Vehicle.name == "7.5 B").first() is None:
    db.session.add(
        Vehicle(
            name="7.5 B",
            required_license_id=License.query.filter(License.name == "C1").first().id,
            rented_from=datetime.now() - timedelta(days=0),
            rented_until=datetime.now() + timedelta(days=2),
        )
    )
if Vehicle.query.filter(Vehicle.name == "7.5 C").first() is None:
    db.session.add(
        Vehicle(
            name="7.5 C",
            required_license_id=License.query.filter(License.name == "C1").first().id,
            rented_from=datetime.now() - timedelta(days=0),
            rented_until=datetime.now() + timedelta(days=2),
        )
    )
if Vehicle.query.filter(Vehicle.name == "40T").first() is None:
    db.session.add(
        Vehicle(
            name="40T",
            required_license_id=License.query.filter(License.name == "CE").first().id,
            rented_from=datetime.now() - timedelta(days=0),
            rented_until=datetime.now() + timedelta(days=2),
        )
    )
db.session.commit()

vehicles = Vehicle.query.all()

organizers = ["CCCV", "NOC", "BOC", "foobar"]
company = ["DHL", "Manfreds tolle Speditions Firma"]
addresses = [
    "CCCV GmbH (Lager Berlin)\nHolzhauser Straße 139\n13509 Berlin",
    "Messe Leipzig\nHalle 4",
    "CCCV GmbH (Lager Leipzig)\nDiezmannstraße 20\n04207 Leipzig",
    "Getränkelieferant Hamburg",
]
owner = ["Spedition XYZ", "CCCV", "Sixt", "private"]
persons = ["Fahrer XYZ, 0123456789", "cpunkt, kennste", "LOC", "Nick Fahrer"]
goods = [
    "Congress is coming, LOC Crew needs to be shipped! Defrosting initialized! Cryo capsules in wake up mode.",
    "Beverages",
    "Popcorn",
    "Merch",
    "Everything!",
    "* Gitterboxen\r\n* Bauzaun\r\n* lauter brandschutzrelevanter Kram",
]
comments = [
    "What a greate comment!\nMultiline!\nGreat line!\n\nGreat!",
    "Whoooohooo",
    "Yipp yipp yipp",
    "<script>alert(1);</script>",
]
# add 12 internal transports starting 2 days ago
for i in range(-2, 10):
    foo = Transport(
        is_internal=True,
        user_id=choice(users).id,
        organizer=choice(organizers),
        origin=choice(addresses),
        destination=choice(addresses),
        goods=choice(goods),
        start=datetime.now()
        + timedelta(days=i, hours=randint(0, 23), minutes=randint(0, 59)),
        duration=timedelta(hours=randint(0, 5)),
        comment=choice(comments),
        not_before=datetime.now()
        + timedelta(days=i - randint(0, 2), hours=0, minutes=0),
        not_after=datetime.now() + timedelta(days=i + randint(1, 3)),
        vehicle_id=choice(vehicles).id,
    )
    db.session.add(foo)
    db.session.commit()

# add 10 external transports
for i in range(0, 10):
    foo = Transport(
        is_internal=False,
        user_id=choice(users).id,
        organizer=choice(company),
        origin=choice(addresses),
        destination=choice(addresses),
        goods=choice(goods),
        start=datetime.now()
        + timedelta(days=i, hours=randint(0, 23), minutes=randint(0, 59)),
        duration=timedelta(hours=randint(0, 5)),
        comment=choice(comments),
    )
    db.session.add(foo)
    db.session.commit()
