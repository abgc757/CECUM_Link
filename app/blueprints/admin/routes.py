"""
INSTRUCCIONES DE INTEGRACIÓN
=============================
1. Reemplaza el contenido de  app/blueprints/admin/routes.py
   con este archivo COMPLETO.
2. Copia db_console.html  →  app/templates/admin/db_console.html
3. No se requieren dependencias extras: usa solo Flask, SQLAlchemy e inspect.
"""

from flask import (
    Blueprint, flash, jsonify, redirect, render_template,
    request, session, url_for,
)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import inspect as sa_inspect, text
from wtforms import IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

from app.extensions import csrf, db
from app.models import Comment, Post, User, UserRole

import csv
import io
import time
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# ──────────────────────────────────────────────
#  Formulario de la consola
# ──────────────────────────────────────────────

class DbConsoleForm(FlaskForm):
    query = TextAreaField("Consulta SQL", validators=[DataRequired()])
    limit = IntegerField(
        "Límite de filas",
        default=200,
        validators=[NumberRange(min=1, max=5_000)],
    )
    submit = SubmitField("Ejecutar")


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

_FORBIDDEN = frozenset({
    "insert", "update", "delete", "drop", "alter",
    "create", "truncate", "replace", "attach", "detach",
    "vacuum", "reindex",
})

_ALLOWED_FIRST = frozenset({"select", "with", "pragma", "explain"})


def _validate_readonly_sql(raw: str):
    """Devuelve un mensaje de error o None si la query es válida."""
    normalized = " ".join(raw.strip().split())
    if not normalized:
        return "La consulta está vacía."
    if normalized.count(";") > 1 or (
        ";" in normalized and not normalized.endswith(";")
    ):
        return "Solo se permite una sentencia SQL por ejecución."

    first = normalized.split()[0].lower()
    if first not in _ALLOWED_FIRST:
        allowed = ", ".join(sorted(_ALLOWED_FIRST)).upper()
        return f"Solo se permiten consultas de lectura ({allowed})."

    tokens = set(normalized.lower().split())
    bad = tokens & _FORBIDDEN
    if bad:
        return f"Palabra(s) prohibida(s) detectada(s): {', '.join(bad).upper()}."

    return None


def _get_schema():
    """
    Devuelve un dict  { table_name: [{"name", "type", "pk", "nullable"}] }
    compatible con SQLite y PostgreSQL.
    """
    insp = sa_inspect(db.engine)
    schema = {}
    for table in insp.get_table_names():
        pk_cols = set(insp.get_pk_constraint(table).get("constrained_columns", []))
        schema[table] = [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "pk": col["name"] in pk_cols,
                "nullable": col.get("nullable", True),
            }
            for col in insp.get_columns(table)
        ]
    return schema


def _run_query(raw_query: str, limit: int):
    """
    Ejecuta la query de solo-lectura y devuelve
    (columns, rows, elapsed_ms, error_msg).
    """
    ql = raw_query.lower().strip().lstrip(";")

    if ql.startswith("pragma"):
        safe_sql = raw_query.rstrip(";")
        params: dict = {}
    else:
        safe_sql = (
            "SELECT * FROM ("
            f"  {raw_query.rstrip(';')}"
            ") AS _q LIMIT :limit"
        )
        params = {"limit": limit}

    t0 = time.perf_counter()
    try:
        result = db.session.execute(text(safe_sql), params)
        mappings = result.mappings().all()
        elapsed = round((time.perf_counter() - t0) * 1_000, 2)
        rows = [dict(m) for m in mappings]
        cols = list(rows[0].keys()) if rows else []
        return cols, rows, elapsed, None
    except Exception as exc:
        elapsed = round((time.perf_counter() - t0) * 1_000, 2)
        return [], [], elapsed, str(exc)


# ──────────────────────────────────────────────
#  Rutas existentes (sin cambios de lógica)
# ──────────────────────────────────────────────

@admin_bp.route("/")
@login_required
def dashboard():
    if not current_user.is_admin:
        flash("Acceso restringido.", "danger")
        return redirect(url_for("posts.feed"))
    users = User.query.order_by(User.created_at.desc()).all()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template(
        "admin/dashboard.html",
        users=users,
        posts=posts,
        roles=[r.value for r in UserRole],
    )


@admin_bp.route("/promote/<int:user_id>", methods=["POST"])
@login_required
def promote(user_id: int):
    if not current_user.is_admin:
        flash("Solo el administrador puede nombrar moderadores.", "danger")
        return redirect(url_for("posts.feed"))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Tu usuario ya es administrador.", "info")
        return redirect(url_for("admin.dashboard"))
    user.role = UserRole.MODERATOR.value
    db.session.commit()
    flash("Usuario promovido a moderador.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/posts/delete/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id: int):
    if not current_user.is_moderator:
        return redirect(url_for("posts.feed"))
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Publicación eliminada.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/review")
@login_required
def review():
    if not current_user.is_moderator:
        flash("Acceso restringido.", "danger")
        return redirect(url_for("posts.feed"))
    archived_posts = (
        Post.query.filter_by(is_archived=True)
        .order_by(Post.archived_at.desc()).all()
    )
    archived_comments = (
        Comment.query.filter_by(is_archived=True)
        .order_by(Comment.archived_at.desc()).all()
    )
    return render_template(
        "admin/review.html",
        archived_posts=archived_posts,
        archived_comments=archived_comments,
    )


@admin_bp.route("/posts/<int:post_id>/unarchive", methods=["POST"])
@login_required
def unarchive_post(post_id: int):
    if not current_user.is_moderator:
        return redirect(url_for("posts.feed"))
    post = Post.query.get_or_404(post_id)
    post.is_archived = False
    post.archived_reason = ""
    post.archived_by = None
    post.archived_at = None
    db.session.commit()
    flash("Publicación restaurada.", "success")
    return redirect(url_for("admin.review"))


@admin_bp.route("/comments/<int:comment_id>/unarchive", methods=["POST"])
@login_required
def unarchive_comment(comment_id: int):
    if not current_user.is_moderator:
        return redirect(url_for("posts.feed"))
    c = Comment.query.get_or_404(comment_id)
    c.is_archived = False
    c.archived_reason = ""
    c.archived_by = None
    c.archived_at = None
    db.session.commit()
    flash("Comentario restaurado.", "success")
    return redirect(url_for("admin.review"))


# ──────────────────────────────────────────────
#  Consola SQL mejorada
# ──────────────────────────────────────────────

_HISTORY_KEY = "db_console_history"
_HISTORY_MAX = 30

PRESET_QUERIES = [
    {
        "label": "Usuarios registrados",
        "icon": "👥",
        "sql": "SELECT id, username, email, role, created_at FROM user ORDER BY created_at DESC",
    },
    {
        "label": "Roles — conteo",
        "icon": "🔐",
        "sql": "SELECT role, COUNT(*) AS total FROM user GROUP BY role ORDER BY total DESC",
    },
    {
        "label": "Posts recientes",
        "icon": "📝",
        "sql": (
            "SELECT p.id, u.username AS autor, p.content, "
            "p.media_type, p.is_archived, p.created_at "
            "FROM post p JOIN user u ON u.id = p.user_id "
            "ORDER BY p.created_at DESC"
        ),
    },
    {
        "label": "Posts por usuario",
        "icon": "📊",
        "sql": (
            "SELECT u.username, COUNT(p.id) AS posts, "
            "SUM(CASE WHEN p.is_archived THEN 1 ELSE 0 END) AS archivados "
            "FROM user u LEFT JOIN post p ON p.user_id = u.id "
            "GROUP BY u.id ORDER BY posts DESC"
        ),
    },
    {
        "label": "Reacciones por tipo",
        "icon": "❤️",
        "sql": (
            "SELECT reaction_type, COUNT(*) AS total "
            "FROM reaction GROUP BY reaction_type ORDER BY total DESC"
        ),
    },
    {
        "label": "Comentarios recientes",
        "icon": "💬",
        "sql": (
            "SELECT c.id, u.username AS autor, c.content, "
            "c.is_archived, c.created_at "
            "FROM comment c JOIN user u ON u.id = c.user_id "
            "ORDER BY c.created_at DESC"
        ),
    },
    {
        "label": "Eventos próximos",
        "icon": "📅",
        "sql": (
            "SELECT e.title, e.location, e.starts_at, e.ends_at, "
            "u.username AS creador "
            "FROM event e JOIN user u ON u.id = e.created_by "
            "ORDER BY e.starts_at ASC"
        ),
    },
    {
        "label": "Chats activos",
        "icon": "💬",
        "sql": (
            "SELECT c.id, c.name, c.is_group, "
            "COUNT(m.id) AS mensajes, c.created_at "
            "FROM conversation c "
            "LEFT JOIN message m ON m.conversation_id = c.id "
            "GROUP BY c.id ORDER BY mensajes DESC"
        ),
    },
    {
        "label": "Tablas — PRAGMA",
        "icon": "🗂️",
        "sql": "PRAGMA table_list",
    },
]


@admin_bp.route("/db-console", methods=["GET", "POST"])
@login_required
def db_console():
    if not current_user.is_moderator:
        flash("Acceso restringido.", "danger")
        return redirect(url_for("posts.feed"))

    form = DbConsoleForm()
    ctx = {
        "form": form,
        "schema": _get_schema(),
        "presets": PRESET_QUERIES,
        "history": session.get(_HISTORY_KEY, []),
        "ran_query": False,
        "columns": [],
        "rows": [],
        "elapsed_ms": 0,
        "error": None,
    }

    if form.validate_on_submit():
        raw = form.query.data.strip().rstrip(";")
        limit = form.limit.data or 200
        err_msg = _validate_readonly_sql(raw)

        if err_msg:
            flash(err_msg, "danger")
        else:
            cols, rows, elapsed, err = _run_query(raw, limit)
            ctx.update(
                ran_query=True,
                columns=cols,
                rows=rows,
                elapsed_ms=elapsed,
                error=err,
            )

            if err:
                flash(f"Error SQL: {err}", "danger")
            else:
                # Historial en sesión
                history: list = session.get(_HISTORY_KEY, [])
                history.insert(0, {
                    "sql": raw,
                    "rows": len(rows),
                    "elapsed": elapsed,
                    "ts": datetime.now().strftime("%H:%M:%S"),
                })
                session[_HISTORY_KEY] = history[:_HISTORY_MAX]
                ctx["history"] = session[_HISTORY_KEY]
                flash(
                    f"{len(rows)} filas · {elapsed} ms",
                    "success",
                )

    elif request.method == "POST":
        flash("Revisa los datos del formulario.", "danger")

    return render_template("admin/db_console.html", **ctx)


# ── API JSON interna (consumida por el JS del template) ──────────────────────

@admin_bp.route("/db-console/schema")
@login_required
def db_console_schema():
    if not current_user.is_moderator:
        return jsonify(error="Forbidden"), 403
    return jsonify(_get_schema())


@admin_bp.route("/db-console/history/clear", methods=["POST"])
@login_required
def db_console_history_clear():
    if not current_user.is_moderator:
        return jsonify(error="Forbidden"), 403
    session.pop(_HISTORY_KEY, None)
    return jsonify(ok=True)


@admin_bp.route("/db-console/export", methods=["POST"])
@csrf.exempt
@login_required
def db_console_export():
    """Recibe JSON {columns, rows} y devuelve CSV."""
    if not current_user.is_moderator:
        return jsonify(error="Forbidden"), 403

    data = request.get_json(silent=True) or {}
    columns: list = data.get("columns", [])
    rows: list = data.get("rows", [])
    fmt: str = data.get("format", "csv")

    if not columns:
        return jsonify(error="Sin columnas"), 400

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        output = buf.getvalue()
        mime = "text/csv"
        ext = "csv"
    else:
        # JSON plano
        import json
        output = json.dumps(rows, ensure_ascii=False, default=str, indent=2)
        mime = "application/json"
        ext = "json"

    from flask import make_response
    resp = make_response(output)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="query_{ts}.{ext}"'
    )
    resp.headers["Content-Type"] = mime
    return resp
