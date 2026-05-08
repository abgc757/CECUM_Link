import os

from flask import Flask

from config import Config

from .extensions import csrf, db, login_manager, migrate, socketio
from . import models  # noqa: F401


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(os.path.join(app.static_folder, "uploads"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    socketio.init_app(app)

    from .blueprints.admin.routes import admin_bp
    from .blueprints.api.routes import api_bp
    from .blueprints.auth.routes import auth_bp
    from .blueprints.chat.routes import chat_bp
    from .blueprints.events.routes import events_bp
    from .blueprints.notifications.routes import notifications_bp
    from .blueprints.posts.routes import posts_bp
    from .commands import create_admin_command

    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.cli.add_command(create_admin_command)

    from .nav_context import register_nav_context   # ← NUEVO
    register_nav_context(app)                        # ← NUEVO

    return app
