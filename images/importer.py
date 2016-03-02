"""Take care of import jobs and copying files. Keep track of import modules"""

import logging
import mimetypes
import os
import re
import base64
from .location import Location, get_locations_by_type, get_location_by_type, IMPORTABLE

re_clean = re.compile(r'[^A-Za-z0-9_\-\.]')

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
from .user import authenticate, require_admin, no_guests, current_user_id
from .file import File, _File, create_file
from .entry import Entry, _Entry, create_entry, get_entries, update_entry_by_id


class App:
    BASE = '/importer'
    
    @classmethod
    def create(self):
        app = bottle.Bottle()
        app.add_hook('before_request', authenticate)

        app.route(
            path='/',
            callback=get_importers_dict,
        )
        app.route(
            path='/trig/<id:int>',
            method='POST',
            callback=lambda id: trig_import(id),
        )
        app.route(
            path='/upload/<source>/<filename>',
            method='POST',
            callback=upload,
        )
        app.route(
            path='/reset/<id:int>',
            method='POST',
            callback=lambda id: reset_entry(id),
        )

        return app


def get_importers_dict():
    no_guests()
    entries = []
    for location in get_locations_by_type(*IMPORTABLE).entries:
        entries.append({
            'location_id': location.id,
            'location_name': location.name,
            'trig_url': get_trig_url(location.id),
        })

    return {
        '*schema': 'ImporterFeed',
        'count': len(entries),
        'entries': entries,
    }


def trig_import(location_id):
    require_admin()
    manager = trig_import.manager
    manager.trig(location_id)
    return {'result': 'ok'}


def upload(source, filename):
    no_guests()
    filename = re_clean.sub('_', os.path.normpath(filename))
    if '..' in filename:
        raise(HTTPError(400))
    location = get_location_by_type(Location.Type.upload)
    folder = location.suggest_folder(source=source)
    try:
        os.makedirs(folder)
    except FileExistsError:
        pass
    destination = os.path.join(folder, filename)
    logging.info("Storing file at %s.", destination)

    
    f = File(
        path=destination,
        location=location,
        purpose=_File.Purpose.source,
    )
    f = create_file(f)
    logging.info(f.to_json())
    e = Entry(
        files=[f],
        import_location_id=location.id,
        state=_Entry.State.import_ready,
        user_id=get_current_user().id,
        source=source,
    )
    e = create_entry(e)
    logging.info(e.to_json())

    with open(destination, 'w+b') as disk:
        data = request.body.read()
        logging.info(request.headers['Content-Type'])
        if request.headers['Content-Type'].startswith('base64'):
            data = base64.b64decode(data[22:])
            logging.info("Writing %i bytes after base64 decode", len(data))
        else:
            logging.info("Writing %i bytes without decode", len(data))
        disk.write(data)
    request.body.close()

    trig_import(location.id)

    return e.to_json()


def get_job_url(location_id):
    return '%s/job/%i' % (App.BASE, location_id)


def get_trig_url(location_id):
    return '%s/trig/%i' % (App.BASE, location_id)


def get_reset_url(import_job_id):
    return '%s/job/%i/reset' % (App.BASE, import_job_id)


# IMPORT MODULE HANDLING
########################

mime_map = {}

def register_import_module(mime_type, module):
    mime_map[mime_type] = module


def get_import_module(mime_type):
    import_module = mime_map.get(mime_type, None)
    return import_module


class GenericImportModule(object):
    def __init__(self, entry):
        self.entry = entry


# API
#####

from datetime import datetime, timedelta
from sqlalchemy.orm.exc import NoResultFound
from samtt import get_db
from .metadata import wrap_raw_json


def pick_up_import_ready_entry(location_id):
    with get_db().transaction() as t:
        try:
            entry = t.query(_Entry).filter(
                _Entry.import_location_id==location_id,
                _Entry.state==_Entry.State.import_ready,
            ).order_by(_Entry.create_ts).first()
            if entry is None:
                return None

            entry.state = _Entry.State.importing
            return Entry.map_in(entry)

        except NoResultFound:
            return None


def fail_import(entry, reason):
    logging.error(reason)
    with get_db().transaction() as t:
        e = t.query(_Entry).get(entry.id)
        e.state = _Entry.State.import_failed
        metadata = wrap_raw_json(e.data) or _Entry.DefaultMetadata()
        metadata.error = reason
        e.data = metadata.to_json()


def reset_entry(entry_id):
    logging.info("Resetting entry %i", entry_id)
    with get_db().transaction() as t:
        e = t.query(_Entry).get(entry_id)
        e.state = _Entry.State.import_ready
        trig_import(e.import_location_id)


# IMPORT MANAGER
################

from threading import Thread, Event


class Manager:
    """
    A Thread+Event based Import Manager that keeps one thread per location
    and trigs a new import round upon the trig method being called.

    There should only be one of these.
    """
    def __init__(self):
        self.events = {}
        trig_import.manager = self

        for location in get_locations_by_type(*IMPORTABLE).entries:
            logging.debug("Setting up import thread [Importer%i].", location.id)
            event = Event()
            self.events[location.id] = event
            thread = Thread(
                target=importing_loop,
                name="Importer%i" % (location.id),
                args=(event, location)
            )
            thread.daemon = True
            thread.start()

    def trig(self, location_id):
        event = self.events.get(location_id)
        if event is None:
            raise NameError("No thread for location %i", location_id)
        logging.info("Trigging import event for location %i", location_id)
        event.set()
                

def importing_loop(import_event, location):
    """
    An import loop that will wait for import_event to be set
    each iteration.
    """
    metadata = location.metadata
    logging.info("Started importer thread for %i:%s", location.id, metadata.folder)
    while True:
        import_event.wait(30)
        import_event.clear()

        while True:
            entry = pick_up_import_ready_entry(location.id)

            if entry is None:
                break

            logging.debug("Entry to import:\n%s", entry.to_json())

            mime_type = guess_mime_type(entry.source_file.full_path)
            ImportModule = get_import_module(mime_type)

            if ImportModule is None:
                fail_import(entry, 
                    "Could not find a suitable import module for MIME Type %s" % mime_type
                )
                continue

            import_module = ImportModule(entry)
            try:
                import_module.run()
            except Exception as e:
                fail_import(entry, 
                    "Import failed %s" % str(e)
                )
                continue

            entry.state = _Entry.State.online
            entry = update_entry_by_id(entry.id, entry, system=True)
            logging.debug("Imported Entry:\n%s", entry.to_json())


def guess_mime_type(file_path):
    mime_type = mimetypes.guess_type(file_path)[0]
    logging.debug("Guessed MIME Type '%s' for '%s'", mime_type, file_path)
    return mime_type
