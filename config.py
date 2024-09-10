from pydantic.v1 import BaseSettings


class Config(BaseSettings):
    HUBSPOT_API_KEY: str
    OPENAI_API_KEY: str
    FLASK_SECRET_KEY: str = "a_default_secret_key"

    class Config:
        env_file = ".env"
