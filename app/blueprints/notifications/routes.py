from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/")
@login_required
def index():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template("notifications/index.html", notifications=items)
