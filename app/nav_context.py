"""
nav_context.py  ─  Contadores del navbar
=========================================

INTEGRACIÓN (3 pasos):

1. Copia este archivo a   app/nav_context.py

2. En  app/__init__.py,  dentro de create_app(), añade:

        from .nav_context import register_nav_context
        register_nav_context(app)

   Ejemplo completo del bloque relevante:

        # ── extensiones ──
        db.init_app(app)
        ...

        # ── blueprints ──
        from .blueprints.admin.routes   import admin_bp
        from .blueprints.api.routes     import api_bp
        ...
        app.register_blueprint(api_bp, url_prefix="/api/v1")

        # ── navbar context ──
        from .nav_context import register_nav_context
        register_nav_context(app)

        return app

3. En  app/blueprints/api/routes.py  agrega el endpoint  /nav-counts:

        @api_bp.get("/nav-counts")
        @login_required
        def nav_counts():
            from app.nav_context import get_nav_counts
            return jsonify(get_nav_counts())

   (El JS de base.html lo llama cada 60 s para refrescar los badges sin recargar.)

──────────────────────────────────────────────────────────────────────────────
LÓGICA DE CONTADORES
──────────────────────────────────────────────────────────────────────────────
  new_posts            → posts publicados en las últimas 24 h que no son del usuario
  upcoming_events      → eventos cuya fecha de inicio es futura
  unread_messages      → mensajes en conversaciones del usuario enviados por otros,
                         recibidos en la última hora  (proxy de "no leídos")
  unread_notifications → notificaciones con is_read = False
  pending_review       → posts + comentarios archivados sin resolver (solo moderadores)

Puedes ajustar las ventanas de tiempo a tu gusto.
"""

from datetime import datetime, timedelta

from flask import jsonify
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    Comment, ConversationMember, Event, Message,
    Notification, Post,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Función central
# ─────────────────────────────────────────────────────────────────────────────

def get_nav_counts() -> dict:
    """
    Devuelve un dict con todos los contadores del navbar.
    Solo se ejecuta cuando hay un usuario autenticado.
    """
    if not current_user.is_authenticated:
        return _empty()

    uid = current_user.id
    now = datetime.utcnow()

    # ── Posts nuevos (últimas 24 h, de otros usuarios, no archivados) ──
    since_posts = now - timedelta(hours=24)
    new_posts = (
        Post.query
        .filter(
            Post.user_id != uid,
            Post.is_archived.is_(False),
            Post.created_at >= since_posts,
        )
        .count()
    )

    # ── Eventos próximos (fecha de inicio futura) ──
    upcoming_events = (
        Event.query
        .filter(Event.starts_at >= now)
        .count()
    )

    # ── Mensajes no leídos (proxy: mensajes de otros en mis chats, < 1 h) ──
    my_conv_ids = [
        m.conversation_id
        for m in ConversationMember.query.filter_by(user_id=uid).all()
    ]
    unread_messages = 0
    if my_conv_ids:
        since_msg = now - timedelta(hours=1)
        unread_messages = (
            Message.query
            .filter(
                Message.conversation_id.in_(my_conv_ids),
                Message.sender_id != uid,
                Message.sent_at >= since_msg,
            )
            .count()
        )

    # ── Notificaciones sin leer ──
    unread_notifications = (
        Notification.query
        .filter_by(user_id=uid, is_read=False)
        .count()
    )

    # ── Revisión pendiente (solo moderadores) ──
    pending_review = 0
    if current_user.is_moderator:
        archived_posts     = Post.query.filter_by(is_archived=True).count()
        archived_comments  = Comment.query.filter_by(is_archived=True).count()
        pending_review     = archived_posts + archived_comments

    return {
        "new_posts":            new_posts,
        "upcoming_events":      upcoming_events,
        "unread_messages":      unread_messages,
        "unread_notifications": unread_notifications,
        "pending_review":       pending_review,
    }


def _empty() -> dict:
    return {
        "new_posts":            0,
        "upcoming_events":      0,
        "unread_messages":      0,
        "unread_notifications": 0,
        "pending_review":       0,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Registro en la app Flask
# ─────────────────────────────────────────────────────────────────────────────

def register_nav_context(app):
    """
    Inyecta `nav_counts` en el contexto de todos los templates Jinja2.
    Llama a esta función en create_app() después de registrar los blueprints.
    """

    @app.context_processor
    def inject_nav_counts():
        return {"nav_counts": get_nav_counts()}
