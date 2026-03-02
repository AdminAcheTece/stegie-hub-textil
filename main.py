import os
from flask import Flask

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Config básica
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
    )

    # Garante que a pasta instance exista
    os.makedirs(app.instance_path, exist_ok=True)

    # Rotas
    from .routes import bp
    app.register_blueprint(bp)

    return app
