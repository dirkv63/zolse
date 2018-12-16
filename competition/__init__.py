# import logging
# import os
from competition import neostore
from config import Config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from lib import my_env

bootstrap = Bootstrap()
lm = LoginManager()
lm.login_view = 'main.login'


def create_app(config_class=Config):
    """
    Create an application instance.

    :param config_class: Pointer to the configuration file.

    :return: the configured application object.
    """
    app = Flask(__name__)
    print("Config Class: {cc}".format(cc=config_class))
    print("Environment: {env}".format(env=app.env))
    # import configuration
    app.config.from_object(config_class)
    # config.py[app.env].init_app(app)
    print("App after config.py setting: {app}".format(app=app))

    # Configure Logger
    my_env.init_loghandler(__name__, app.config.get('LOGDIR'), app.config.get('LOGLEVEL'))

    # initialize extensions
    bootstrap.init_app(app)
    lm.init_app(app)

    """
    os.environ['Neo4J_User'] = app.config.py.get('NEO4J_USER')
    os.environ['Neo4J_Pwd'] = app.config.py.get('NEO4J_PWD')
    os.environ['Neo4J_Db'] = app.config.py.get('NEO4J_DB')
    try:
        os.environ['Neo4J_Host'] = app.config.py.get('NEO4J_HOST')
    except TypeError:
        pass
    """
    # import blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    # configure production logging of errors
    return app
