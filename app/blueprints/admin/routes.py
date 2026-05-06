from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Post, User, UserRole

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
def dashboard():
    if not current_user.is_moderator:
        flash("Acceso restringido.", "danger")
        return redirect(url_for("posts.feed"))
    users = User.query.order_by(User.created_at.desc()).all()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin/dashboard.html", users=users, posts=posts, roles=[r.value for r in UserRole])


@admin_bp.route("/promote/<int:user_id>", methods=["POST"])
@login_required
def promote(user_id: int):
    if not current_user.is_moderator:
        return redirect(url_for("posts.feed"))
    user = User.query.get_or_404(user_id)
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
