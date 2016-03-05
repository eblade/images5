import logging


# DB MODEL
##########

from enum import IntEnum
from sqlalchemy import Column, String, Integer
from samtt import Base
from .types import PropertySet, Property


class _User(Base):
    __tablename__ = 'user'

    class Status(IntEnum):
        disabled = 0
        enabled = 1

    class Class(IntEnum):
        normal = 0
        admin = 1
        guest = 2

    id = Column(Integer, primary_key=True)
    status = Column(Integer, nullable=False, default=Status.enabled)
    name = Column(String(128), nullable=False)
    fullname = Column(String(128), nullable=False)
    password = Column(String(128), nullable=False)
    user_class = Column(Integer, nullable=False, default=Class.normal)


# DESCRIPTOR
############


class User(PropertySet):
    id = Property(int)
    status = Property(enum=_User.Status)
    name = Property()
    fullname = Property()
    user_class = Property(enum=_User.Class)

    @classmethod
    def map_in(self, user):
        return User(
            id = user.id,
            status = _User.Status(user.status),
            name = user.name,
            fullname = user.fullname,
            user_class = _User.Class(user.user_class)
        )


# WEB
#####

import bottle
from .web import (
    Create,
    Fetch,
    FetchByKey,
    FetchById,
    FetchByQuery,
)


class App:
    BASE = '/user'
    
    @classmethod
    def create(self):
        app = bottle.Bottle()
        app.add_hook('before_request', authenticate)

        app.route(
            path='/me',
            method='GET',
            callback=me,
        )
        app.route(
            path='/<id:int>',
            method='GET',
            callback=FetchById(
                get_user_by_id,
                pre=require_admin
            ),
        )
        app.route(
            path='/name/<key>',
            method='GET',
            callback=FetchByKey(
                get_user_by_name,
                pre=require_admin
            ),
        )

        return app


def me():
    json = bottle.request.user.to_json()
    logging.info("Me\n%s", json)
    return json


# UTILS
#######

import hashlib
from samtt import get_db
from sqlalchemy.orm.exc import NoResultFound


def basic_auth(username, password):
    """
    Bottle-compatible simple-checker that stores the user descriptor
    of the currently logged in user onto the request.
    """
    with get_db().transaction() as t:
        try:
            user = (t.query(_User)
                     .filter(_User.name==username)
                     .filter(_User.password==password_hash(password))
                     .filter(_User.status==_User.Status.enabled)
                     .one())

            bottle.request.user = User(
                id=user.id,
                status=_User.Status(user.status),
                name=user.name,
                fullname=user.fullname,
                user_class=_User.Class(user.user_class),
            )
            logging.debug("Logged in as %s", user.name)
            return True
        except NoResultFound:
            return False


def authenticate(*args, realm='images'):
    """
    Bottle hook for authentication using basic auth
    """
    username, password = bottle.request.auth or (None, None)
    if username is None or not basic_auth(username, password):
        err = bottle.HTTPError(401, "Authentication failed")
        err.add_header('WWW-Authenticate', 'Basic realm="%s"' % realm)
        raise err


def require_admin(*args, realm="private"):
    """
    Bottle hook for requiring an Admin account
    """
    if not current_is_admin():
        err = bottle.HTTPError(401, "Admin permission required")
        err.add_header('WWW-Authenticate', 'Basic realm="%s"' % realm)
        return err


def no_guests(*args):
    """
    Bottle hook for requiring higher class than Guest
    """
    if bottle.request.user.user_class is _User.Class.guest:
        err = bottle.HTTPError(401, "Guests not allowed")
        return err


def password_hash(string):
    return hashlib.sha512(string.encode('utf8')).hexdigest()

# API
#####


def current_user_id():
    """
    Shorthand for retrieving the currently logged in user, if any.
    """
    try:
        return bottle.request.user.id
    except AttributeError:
        return None


def current_is_user():
    return bottle.request.user.user_class is not _User.Class.guest


def current_is_admin():
    return bottle.request.user.user_class is _User.Class.admin


def current_is_guest():
    return bottle.request.user.user_class is _User.Class.guest


def require_user_id(user_id):
    """
    Shorthand for requiring a certain user or raise a 401
    """
    if user_id != bottle.request.user.id:
        raise bottle.HTTPError(401, "Access denied")


def get_user_by_id(user_id):
    with get_db().transaction() as t:
        try:
            user = (t.query(_User)
                     .filter(_User.id == user_id)
                     .one())
            return User.map_in(user)
        except NoResultFound:
            raise bottle.HTTPError(404)


def get_user_by_name(name):
    with get_db().transaction() as t:
        try:
            user = (t.query(_User)
                     .filter(_User.name == name)
                     .one())
            return User.map_in(user)
        except NoResultFound:
            raise bottle.HTTPError(404)

