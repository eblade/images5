import logging
import datetime
import os


# DB MODEL
##########

from samtt import Base, get_db
from sqlalchemy import Column, String, Integer
from .metadata import register_metadata_schema
from .types import Property, PropertySet


class _Location(Base):
    __tablename__ = 'location'

    class DefaultLocationMetadata(PropertySet):
        server = Property()
        folder = Property()
        subfolder = Property(default='{date}')
        user_id = Property(int)
        keep_original = Property(bool, default=False)
        source = Property()
        tags = Property(list)
        read_only = Property(bool)
        wants = Property(list)  # File.Purpose

    id = Column(Integer, primary_key=True)
    type = Column(String(128), nullable=True)
    name = Column(String(128), nullable=False)
    data = Column(String(512))


register_metadata_schema(_Location.DefaultLocationMetadata)


SCANNABLE = ('drop', )
IMPORTABLE = ('drop', 'upload')


############
# DESCRIPTOR 

from enum import IntEnum
from .types import Property, PropertySet
from .metadata import wrap_raw_json


class Location(PropertySet):

    type = Property()
    id = Property(int)
    name = Property()
    metadata = Property(wrap=True)

    trig_scan_url = Property()
    trig_import_url = Property()

    def __repr__(self):
        if self.id:
            return (
                '<Location %i %s [%s]>' %
                (self.id or 0, self.name, self.type or '?')
            )
        else:
            return '<Location>'

    def suggest_folder(self, **hints):
        folder = self.metadata.folder
        if 'date' not in hints:
            hints['date'] = datetime.date.today().isoformat()
        if 'type' not in hints:
            hints['type'] = 'unknown'
        if 'source' not in hints:
            hints['source'] = 'unknown'
        subfolder = self.metadata.subfolder.format(**hints)
        return os.path.join(folder, subfolder)

    @property
    def root(self):
        return self.metadata.folder

    def calculate_urls(self):
        self.self_url = '%s/%i' % (App.BASE, self.id)
        #self.trig_scan_url = api.url().scanner.get_trig_url(self.id)
        #self.trig_import_url = api.url().import_job.get_trig_url(self.id)

    @classmethod
    def map_in(self, location):
        ld = Location( 
            id=location.id,
            type=location.type,
            name=location.name,
            metadata=wrap_raw_json(location.data),
        )
        ld.calculate_urls()
        return ld

    def map_out(self, location):
       location.name = self.name
       location.type = self.type
       location.data = self.metadata.to_json() \
                       if self.metadata is not None else None


class LocationFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


# WEB
#####

import bottle
from .web import (
    Create,
    Fetch,
    FetchByKey,
    FetchById,
    FetchByQuery,
    UpdateById,
    DeleteById,
)
from .user import authenticate, require_admin


class App:
    BASE = '/location'
    
    @classmethod
    def create(self):
        app = bottle.Bottle()
        app.add_hook('before_request', authenticate)

        app.route(
            path='/',
            method='POST',
            callback=Create(
                create_location,
                Location,
                pre=require_admin
            ),
        )
        app.route(
            path='/',
            method='GET',
            callback=Fetch(
                get_locations,
                pre=require_admin
            ),
        )
        app.route(
            path='/<id:int>',
            method='GET',
            callback=FetchById(
                get_location_by_id,
                pre=require_admin
            ),
        )
        app.route(
            path='/<id:int>',
            method='PUT',
            callback=UpdateById(
                update_location_by_id,
                Location,
                pre=require_admin
            ),
        )
        app.route(
            path='/<id:int>',
            method='DELETE',
            callback=DeleteById(
                delete_location_by_id,
                pre=require_admin
            ),
        )
        app.route(
            path='/<id:int>/dl/<path:path>',
            method='GET',
            callback=download,
        )

        return app


def download(id, path):
    location = get_location_by_id(id)
    return bottle.static_file(path, root=location.metadata.folder)


# API
#####


def get_location_by_id(id):
    with get_db().transaction() as t:
        location = t.query(_Location).filter(_Location.id==id).one()
        return Location.map_in(location)


def get_location_by_name(name):
    with get_db().transaction() as t:
        location = t.query(_Location).filter(_Location.name==name).one()
        return Location.map_in(location)


def get_locations_by_type(*types):
    with get_db().transaction() as t:
        locations = t.query(_Location).filter(_Location.type.in_(types)).all()
        return LocationFeed(
            count=len(locations),
            entries=[Location.map_in(location) for location in locations]
        )


def get_location_by_type(type):
    locations = get_locations_by_type(type)
    return locations.entries[0]


def get_locations():
    with get_db().transaction() as t:
        locations = t.query(_Location).all()
        return LocationFeed(
            count=len(locations),
            entries=[Location.map_in(location) for location in locations]
        )


def delete_file_on_location(location, path):
    try:
        os.remove(os.path.join(location.metadata.folder, path))
    except FileNotFoundError:
        logging.warning(
            'File "%i:%s" cannot be deleted, since it\'s already gone',
            location.id,
            path
        )


def create_location(ld):
    with get_db().transaction() as t:
        location = _Location()
        ld.map_out(location)
        t.add(location)
        t.commit()
        id = location.id
    return get_location_by_id(id)


def update_location_by_id(id, ld):
    with get_db().transaction() as t:
        q = t.query(_Location).filter(_Location.id==id)
        location = q.one()
        ld.map_out(location)

    return get_location_by_id(id)


def delete_location_by_id(id):
    with get_db().transaction() as t:
        q = t.query(_Location).filter(_Location.id==id).delete()
