import logging
from flask import Flask

from config import Config
from router import create_routes


def initialize_app(configuration: Config) -> Flask:
    flask_instance = Flask(__name__)
    flask_instance.secret_key = configuration.FLASK_SECRET_KEY

    logging.basicConfig(level=logging.INFO)

    create_routes(flask_instance, configuration)

    return flask_instance


if __name__ == "__main__":
    config_instance = Config()
    flask_app = initialize_app(config_instance)
    flask_app.run(debug=True)
