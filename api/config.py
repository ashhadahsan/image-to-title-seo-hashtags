import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


class BaseConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "imagedata.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "KEYSOSECRETGETSYOURMOMMAWETTT123"
    JWT_SECRET_KEY = "secretkeyssbabe"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_USERNAME = "ABC@gmail.com"
    MAIL_PASSWORD = "PASSWORD"
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    UPLOADED_IMAGES_DEST = "./images"
    UPLOADED_PHOTOS_DEST = "./images"
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024
