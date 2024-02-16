from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from geopy.distance import geodesic
from datetime import datetime, timezone


app = Flask(__name__)
app.config.from_object("project.config.Config")
db = SQLAlchemy(app)


DISTANCE_THRESHOLD = float(app.config.get("DISTANCE_THRESHOLD"))
TIME_THRESHOLD = float(app.config.get("TIME_THRESHOLD"))


def safe_cast(val, to_type, default=0.00):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


class Point(db.Model):
    __tablename__ = "points"

    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.Integer)
    alt = db.Column(db.Float)
    batt = db.Column(db.Float)
    tst = db.Column(db.TIMESTAMP(timezone=True))
    vel = db.Column(db.Float)
    tid = db.Column(db.String)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    acc = db.Column(db.Float)
    sat = db.Column(db.Integer)
    geom = db.Column(Geometry(geometry_type='POINT', srid=4326))

    def __init__(self, track_id, alt, batt, tst, vel, tid, lat, lon, acc, sat, geom):
        self.track_id = track_id
        self.alt = alt
        self.batt = batt
        self.tst = tst
        self.vel = vel
        self.tid = tid
        self.lat = lat
        self.lon = lon
        self.acc = acc
        self.sat = sat
        self.geom = geom


class Track(db.Model):
    __tablename__ = "tracks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_time = db.Column(db.TIMESTAMP(timezone=True))
    end_time = db.Column(db.TIMESTAMP(timezone=True))
    geom = db.Column(Geometry(geometry_type='LINESTRING', srid=4326))

    def __init__(self, start_time, end_time, geom):
        self.start_time = start_time
        self.end_time = end_time
        self.geom = geom


@app.route('/post', methods=["POST"])
def post():
    content_type = request.headers.get('Content-Type')

    if content_type and 'application/json' in content_type:
        lat = request.get_json().get('lat', '')
        lon = request.get_json().get('lon', '')
        tst = request.get_json().get('tst', '')
        alt = round(safe_cast(request.get_json().get('alt', ''), float), 2)
        acc = round(safe_cast(request.get_json().get('acc', ''), float), 2)
        vel = round(safe_cast(request.get_json().get('vel', ''), float), 2)
        sat = request.get_json().get('sat', '')
        batt = request.get_json().get('batt', '')
        tid = request.get_json().get('tid', '')
    else:
        lat = request.form.get('lat')
        lon = request.form.get('lon')
        tst = int(request.form.get('tst'))
        alt = round(safe_cast(request.form.get('alt'), float), 2)
        acc = round(safe_cast(request.form.get('acc'), float), 2)
        vel = round(safe_cast(request.form.get('vel'), float), 2)
        sat = request.form.get('sat')
        batt = request.form.get('batt')
        tid = request.form.get('tid')

    point_wkt = 'POINT({} {})'.format(lon, lat)
    this_point_tst = datetime.fromtimestamp(tst, tz=timezone.utc)
    prev_point = Point.query.order_by(Point.tst.desc()).first()

    if prev_point:
        distance_to_last = geodesic((prev_point.lat, prev_point.lon), (lat, lon)).meters
        time_to_last = (this_point_tst - prev_point.tst.astimezone(tz=timezone.utc)).seconds

        # if this point is more than 500m or 900s from the previous point, create new track ID
        # do nothing else at this point because we can't create a linestring with just one point
        if distance_to_last > DISTANCE_THRESHOLD or time_to_last > TIME_THRESHOLD:
            track_id = prev_point.track_id + 1

        # this point belongs to the current track, so give it the same track ID as the previous point
        else:
            track_id = prev_point.track_id

            # if this is the second point for the track ID we can create the linestring
            if Point.query.filter_by(track_id=track_id).count() == 1:
                track = Track(
                    start_time=prev_point.tst,
                    end_time=this_point_tst,
                    geom='LINESTRING({} {}, {} {})'.format(prev_point.lon, prev_point.lat, lon, lat)
                )
                db.session.add(track)
            # if it is not the second point, add it to the existing linestring points and update the end time
            else:
                current_track = Track.query.filter_by(id=track_id).first()

                if current_track:
                    current_track.geom = func.ST_AddPoint(current_track.geom, point_wkt)
                    current_track.end_time = prev_point.tst

    # there are no points yet, start fresh with a track ID of 1
    else:
        track_id = 1

    # Add the Point object to the session and commit the changes
    point = Point(
        track_id=track_id,
        alt=alt,
        batt=batt,
        tst=this_point_tst,
        vel=vel,
        tid=tid,
        lat=lat,
        lon=lon,
        acc=acc,
        sat=sat,
        geom=point_wkt
    )
    print(point)
    db.session.add(point)
    db.session.commit()

    return 'Data submitted!'
