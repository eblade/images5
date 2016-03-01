import sys
import os
import logging
import configparser

from samtt import init
from .location import _Location
from .user import _User, password_hash
from .location import get_location_by_name, update_location_by_id

class Setup:
    def __init__(self, config_path, debug=False):
        self.setup_logging(debug=debug)
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        logging.info("Config read from %s", config_path)

        self.setup_database()
        self.setup_server()

    def setup_logging(self, debug=False):
        FORMAT = '%(asctime)s [%(threadName)s] %(filename)s +%(levelno)s ' + \
                 '%(funcName)s %(levelname)s %(message)s'
        logging.basicConfig(
            format=FORMAT,
            level=(logging.DEBUG if debug else logging.INFO),
        )

    def setup_database(self):
        sql_path = self.config['Database']['path']
        logging.debug("SQL Path: %s", sql_path)
        logging.debug("Connecting to the Database...")
        self.db = init(sql_path)

    def setup_server(self):
        self.server_host = self.config['Server']['host']
        self.server_port = int(self.config['Server']['port'])

    def create_database_tables(self):
        logging.info("Creating tables...")
        self.db.create_all()

    def add_users(self):
        logging.info("Setting up users...")
        with self.db.transaction() as t:
            for username, data in self.config['User'].items():
                logging.debug("There should be a user '%s'.", username)
                
                if t.query(_User).filter(_User.name==username).count() > 0:
                    logging.debug("User '%s' exists, skipping.", username)
                    continue

                data = [d.strip() for d in data.split(',')]
                assert len(data) == 3, "username = Fullname, Class, State"
                fullname = data[0]
                user_class = getattr(_User.Class, data[1])
                status = getattr(_User.Status, data[2])

                user = _User(
                    name=username,
                    fullname=fullname,
                    user_class=user_class,
                    status=status,
                    password=password_hash(username),
                )
                t.add(user)
                logging.info("Added user '%s'.", username)
        logging.info("Done with users.")

    def add_locations(self):
        logging.info("Setting up locations...")
        with self.db.transaction() as t:
            for name, path in self.config['Location'].items():
                logging.debug("There should be a location '%s'.", name)

                if t.query(_Location).filter(_Location.name==name).count() > 0:
                    logging.debug("Location '%s' exists, updating.", name)
                    location = get_location_by_name(name)
                    location.metadata.folder = path
                    update_location_by_id(location.id, location)
                    continue

                extra_name = 'Location:%s' % name
                extra = (self.config[extra_name] 
                         if extra_name in self.config.sections() 
                         else {})
                extra = {k: v for k, v in extra.items()}
                if 'wants' in extra:
                    extra['wants'] = [
                        b.strip() for b in extra['wants'].split(',') if b
                    ]
                if 'tags' in extra:
                    extra['tags'] = [
                        b.strip() for b in extra['tags'].split(',') if b
                    ]

                metadata = data=_Location.DefaultLocationMetadata(extra)
                metadata.folder = path
                type = extra.get('type', name)
            
                location = _Location(
                    name=name,
                    type=type,
                    data=metadata.to_json(),
                )
                
                t.add(location)
                logging.info("Added location '%s'.", name)
        logging.info("Done with locations.")
