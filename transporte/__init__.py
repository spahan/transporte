from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_assets import Environment

db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
assets = Environment()


def create_app():
    """Construct the core application."""
    app = Flask(__name__)
    app.config.from_pyfile("config.cfg")
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    assets.init_app(app)

    with app.app_context():
        from . import views  # noqa: F401
        from .util import bundles

        db.create_all()
        assets.register(bundles)
        return app
