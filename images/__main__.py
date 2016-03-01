import os
import logging
import argparse

from .setup import Setup

from . import web
from . import user
from . import tag
from . import entry
from . import file
from . import location
from . import scanner


if __name__ == '__main__':
    # Options
    parser = argparse.ArgumentParser(usage="images")
    parser.add_argument(
        '-c', '--config',
         default=os.getenv('IMAGES_CONFIG', 'images.ini'),
        help='specify what config file to run on')
    parser.add_argument(
        '-g', '--debug', action="store_true",
        help='show debug messages')

    args = parser.parse_args()

    # Config and Database
    setup = Setup(args.config, debug=args.debug)
    logging.info("*** Setting up Database...")
    setup.create_database_tables()
    setup.add_users()
    setup.add_locations()
    logging.info("*** Done setting up Databse.") 

    # Setting up workers
    logging.info("*** Setting up Workers...")
    managers = []
    for module in (scanner, ):
        logging.info("Starting %s manager..." % (module.__name__))
        managers.append(module.Manager())
    logging.info("*** Done setting up Workers.") 

    # Web-Apps
    logging.info("*** Setting up Web-Apps...")
    app = web.App.create()
    for module in (
        location,
        user,
        entry,
        tag,
        scanner,
    ):
        logging.info(
            "Setting up %s on %s..." % (module.__name__, module.App.BASE)
        )
        app.mount(module.App.BASE, module.App.create())
    logging.info("*** Done setting up Web-apps.") 

    # Serve the Web-App
    app.run(
        host=setup.server_host,
        port=setup.server_port,
    )
