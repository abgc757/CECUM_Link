from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import text
from wtforms import IntegerField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange

from app.extensions import db
from app.models import Comment, Post, User, UserRole

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


class DbConsoleForm(FlaskForm):
    query = TextAreaField("Consulta SQL", validators=[DataRequired()])
    limit = IntegerField("Limite de filas", default=200, validators=[NumberRange(min=1, max=5000)])
    submit = SubmitField("Ejecutar")


def _validate_readonly_sql(query: str):
    normalized = " ".join((query or "").strip().split())
    if not normalized:
        return "La consulta esta vacia."
    if ";" in normalized.rstrip(";"):
        return "Solo se permite una sentencia SQL por consulta."
    first_word = normalized.split(" ", 1)[0].lower()
    if first_word not in {"select", "with", "pragma"}:
        return "Solo se permiten consultas de lectura (SELECT/WITH/PRAGMA)."
    forbidden = {"insert", "update", "delete", "drop", "alter", "create", "truncate", "replace"}
    lowered = normalized.lower()
    if any(token in lowered for token in forbidden):
        return "La consulta contiene comandos no permitidos."
    return None


@admin_bp.route("/")
@login_required
def dashboard():
    if not current_user.is_admin:
        flash("Acceso restringido.", "danger")
        return redirect(url_for("posts.feed"))
    users = User.query.order_by(User.created_at.desc()).all()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin/dashboard.html", users=users, posts=posts, roles=[r.value for r in UserRole])


@admin_bp.route("/promote/<int:user_id>", methods=["POST"])
@login_required
def promote(user_id: int):
    if not current_user.is_admin:
        flash("Solo el administrador del sistema puede nombrar moderadores.", "danger")
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
    flash("Publicacion eliminada.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/review")
@login_required
def review():
    if not current_user.is_moderator:
        flash("Acceso restringido.", "danger")
        return redirect(url_for("posts.feed"))
    archived_posts = Post.query.filter_by(is_archived=True).order_by(Post.archived_at.desc()).all()
    archived_comments = Comment.query.filter_by(is_archived=True).order_by(Comment.archived_at.desc()).all()
    return render_template("admin/review.html", archived_posts=archived_posts, archived_comments=archived_comments)


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
    flash("Publicacion restaurada.", "success")
    return redirect(url_for("admin.review"))


@admin_bp.route("/comments/<int:comment_id>/unarchive", methods=["POST"])
@login_required
def unarchive_comment(comment_id: int):
    if not current_user.is_moderator:
        return redirect(url_for("posts.feed"))
    comment_obj = Comment.query.get_or_404(comment_id)
    comment_obj.is_archived = False
    comment_obj.archived_reason = ""
    comment_obj.archived_by = None
    comment_obj.archived_at = None
    db.session.commit()
    flash("Comentario restaurado.", "success")
    return redirect(url_for("admin.review"))


@admin_bp.route("/db-console", methods=["GET", "POST"])
@login_required
def db_console():
    if not current_user.is_moderator:
        flash("Acceso restringido.", "danger")
        return redirect(url_for("posts.feed"))

    form = DbConsoleForm()
    rows = []
    columns = []
    ran_query = False
    if form.validate_on_submit():
        ran_query = True
        query = form.query.data.strip()
        error = _validate_readonly_sql(query)
        if error:
            flash(error, "danger")
            return render_template("admin/db_console.html", form=form, rows=rows, columns=columns, ran_query=ran_query)
        safe_query = f"SELECT * FROM ({query}) AS q LIMIT :limit" if not query.lower().startswith("pragma") else query
        params = {"limit": form.limit.data or 200}
        result = db.session.execute(text(safe_query), params if "limit" in safe_query else {})
        mappings = result.mappings().all()
        rows = [dict(item) for item in mappings]
        if rows:
            columns = list(rows[0].keys())
        flash(f"Consulta ejecutada. Filas: {len(rows)}", "success")
    elif request.method == "POST":
        flash("Revisa la consulta y vuelve a intentar.", "danger")

    return render_template("admin/db_console.html", form=form, rows=rows, columns=columns, ran_query=ran_query)
