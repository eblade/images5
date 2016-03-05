import os
import logging
import bottle

from threading import Thread, Event

from .location import get_locations_by_type, SCANNABLE
from .file import _File, File, create_file
from .entry import _Entry, Entry, create_entry
from .user import authenticate, require_admin, no_guests


# WEB
#####


class App:
    BASE = '/scanner'

    @classmethod
    def create(self):
        app = bottle.Bottle()
        app.add_hook('before_request', authenticate)

        app.route(
            path='/',
            callback=get_scanners_dict,
        )
        app.route(
            path='/trig/<id:int>',
            method='POST',
            callback=lambda id: trig_scan(id),
        )

        return app


def get_scanners_dict():
    no_guests()
    entries = []
    for location in get_locations_by_type(*SCANNABLE).entries:
        entries.append({
            'location_id': location.id,
            'location_name': location.name,
            'trig_url': get_trig_url(location.id),
        })

    return {
        '*schema': 'ScannerFeed',
        'count': len(entries),
        'entries': entries,
    }


def trig_scan(location_id):
    require_admin()
    manager = trig_scan.manager
    manager.trig(location_id)
    return {'result': 'ok'}


def get_trig_url(location_id):
    return '%s/trig/%s' % (App.BASE, location_id)


# LOCAL FOLDER SCANNER
######################


class FolderScanner(object):
    """
    A simple recursive folder scanner.
    """
    def __init__(self, basepath, ext=None):
        self.basepath = basepath
        self.ext = ext

    def scan(self):
        for r, ds, fs in os.walk(self.basepath):
            for f in fs:
                if not self.ext or f.split('.')[-1].lower() in self.ext:
                    p = os.path.relpath(os.path.join(r, f), self.basepath)
                    if not p.startswith('.'):
                        yield p


# SCANNER MANAGER
#################


class Manager:
    """
    A Thread+Event based Scanner Manager that keeps one thread per folder
    and trigs a new scan upon the trig method being called.

    There should only be one of these.
    """
    def __init__(self):
        self.events = {}
        trig_scan.manager = self

        for location in get_locations_by_type(*SCANNABLE).entries:
            logging.debug("Setting up scanner thread [Scanner%i]", location.id)
            event = Event()
            self.events[location.id] = event
            thread = Thread(
                target=scanning_loop,
                name="Scanner%i" % (location.id),
                args=(event, location)
            )
            thread.daemon = True
            thread.start()

    def trig(self, location_id):
        event = self.events.get(location_id)
        if event is None:
            raise ValueError("No thread for location %i", location_id)
        logging.info("Triggering scanner event for location %i", location_id)
        event.set()


def scanning_loop(scan_event, location):
    """
    A scanning loop using FolderScanner. Will wait for scan_event to be set
    each iteration.
    """
    metadata = location.metadata
    logging.info("Started scanner thread for %i:%s", location.id, metadata.folder)
    while True:
        scanner = FolderScanner(metadata.folder, ext=None)

        scan_event.wait(30)
        scan_event.clear()

        for filepath in scanner.scan():
            try:
                f = File(
                    path=filepath,
                    location=location,
                    purpose=_File.Purpose.source,
                )
                f = create_file(f)
                logging.info(f.to_json())
                e = Entry(
                    files=[f],
                    import_location_id=location.id,
                    state=_Entry.State.import_ready,
                    user_id=metadata.user_id,
                    tags=metadata.tags,
                )
                e = create_entry(e)
                logging.info(e.to_json())
            except _File.ConflictException:
                logging.debug("File '%s' is managed", filepath)
