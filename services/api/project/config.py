import os


basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite://")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DISTANCE_THRESHOLD = os.getenv("DISTANCE_THRESHOLD", 500)
    TIME_THRESHOLD = os.getenv("TIME_THRESHOLD", 900)
