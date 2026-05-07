from collections import Counter
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from werkzeug.utils import secure_filename
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.extensions import db
from app.models import Comment, Post, Reaction, ReactionType

posts_bp = Blueprint("posts", __name__)


class PostForm(FlaskForm):
    content = TextAreaField("Publicacion", validators=[DataRequired(), Length(max=2000)])
    media = FileField("Multimedia")
    submit = SubmitField("Publicar")


class CommentForm(FlaskForm):
    content = TextAreaField("Comentario", validators=[DataRequired(), Length(max=1000)])
    tagged_users = StringField("Etiquetas (usuario1,usuario2)")
    submit = SubmitField("Comentar")


@posts_bp.route("/", methods=["GET", "POST"])
@login_required
def feed():
    form = PostForm()
    if form.validate_on_submit():
        media_url = ""
        media_type = "text"
        uploaded = form.media.data
        if uploaded and getattr(uploaded, "filename", ""):
            ext = Path(uploaded.filename).suffix.lower()
            allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".webm"}
            if ext not in allowed:
                flash("Formato no permitido. Usa imagen o video.", "danger")
                return redirect(url_for("posts.feed"))

            filename = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{secure_filename(uploaded.filename)}"
            upload_dir = Path(current_app.static_folder) / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            uploaded.save(upload_dir / filename)
            media_url = url_for("static", filename=f"uploads/{filename}")
            media_type = "video" if ext in {".mp4", ".mov", ".webm"} else "photo"

        post = Post(
            content=form.content.data.strip(),
            media_url=media_url,
            media_type=media_type,
            external_link="",
            user_id=current_user.id,
        )
        db.session.add(post)
        db.session.commit()
        flash("Publicacion creada.", "success")
        return redirect(url_for("posts.feed"))

    posts = Post.query.filter_by(is_archived=False).order_by(Post.created_at.desc()).all()
    comment_form = CommentForm()
    reaction_stats = {}
    for post in posts:
        counts = Counter([reaction.reaction_type for reaction in post.reactions])
        reaction_stats[post.id] = dict(counts)

    return render_template(
        "posts/feed.html",
        form=form,
        posts=posts,
        comment_form=comment_form,
        reaction_stats=reaction_stats,
    )


@posts_bp.route("/posts/<int:post_id>/react/<reaction_type>", methods=["POST"])
@login_required
def react(post_id: int, reaction_type: str):
    if reaction_type not in {r.value for r in ReactionType}:
        flash("Reaccion no valida.", "danger")
        return redirect(url_for("posts.feed"))

    reaction = Reaction.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    if reaction:
        reaction.reaction_type = reaction_type
    else:
        reaction = Reaction(post_id=post_id, user_id=current_user.id, reaction_type=reaction_type)
        db.session.add(reaction)
    db.session.commit()
    return redirect(url_for("posts.feed"))


@posts_bp.route("/posts/<int:post_id>/comment", methods=["POST"])
@login_required
def comment(post_id: int):
    form = CommentForm()
    if form.validate_on_submit():
        comment_obj = Comment(
            content=form.content.data.strip(),
            tagged_users=form.tagged_users.data or "",
            user_id=current_user.id,
            post_id=post_id,
        )
        db.session.add(comment_obj)
        db.session.commit()
        flash("Comentario agregado.", "success")
    else:
        flash("Comentario invalido.", "danger")
    return redirect(url_for("posts.feed"))


@posts_bp.route("/posts/<int:post_id>/archive", methods=["POST"])
@login_required
def archive_post(post_id: int):
    if not current_user.is_moderator:
        flash("Solo moderadores/docentes pueden archivar publicaciones.", "danger")
        return redirect(url_for("posts.feed"))
    post = Post.query.get_or_404(post_id)
    reason = (request.form.get("reason") or "").strip()
    post.is_archived = True
    post.archived_reason = reason[:255]
    post.archived_by = current_user.id
    post.archived_at = datetime.utcnow()
    db.session.commit()
    flash("Publicacion archivada para revision.", "info")
    return redirect(url_for("posts.feed"))


@posts_bp.route("/comments/<int:comment_id>/archive", methods=["POST"])
@login_required
def archive_comment(comment_id: int):
    if not current_user.is_moderator:
        flash("Solo moderadores/docentes pueden archivar comentarios.", "danger")
        return redirect(url_for("posts.feed"))
    comment_obj = Comment.query.get_or_404(comment_id)
    reason = (request.form.get("reason") or "").strip()
    comment_obj.is_archived = True
    comment_obj.archived_reason = reason[:255]
    comment_obj.archived_by = current_user.id
    comment_obj.archived_at = datetime.utcnow()
    db.session.commit()
    flash("Comentario archivado para revision.", "info")
    return redirect(url_for("posts.feed"))
