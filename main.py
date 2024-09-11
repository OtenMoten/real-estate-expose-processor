import logging
from flask import Flask
from config import Config
from router import create_routes


def create_app(config: Config = None) -> Flask:

    if config is None:
        config = Config()

    flask_instance = Flask(__name__)
    flask_instance.secret_key = config.FLASK_SECRET_KEY

    logging.basicConfig(level=logging.INFO)

    create_routes(flask_instance, config)

    return flask_instance


flask_app = create_app()

if __name__ == "__main__":
    flask_app.run(debug=True)
