from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Event, Post

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "cecum-link-api"})


@api_bp.get("/posts")
def list_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    payload = [
        {
            "id": p.id,
            "content": p.content,
            "media_url": p.media_url,
            "media_type": p.media_type,
            "external_link": p.external_link,
            "author_id": p.user_id,
            "created_at": p.created_at.isoformat(),
        }
        for p in posts
    ]
    return jsonify(payload)


@api_bp.post("/posts")
@login_required
def create_post():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400
    post = Post(
        content=content,
        media_url=data.get("media_url", ""),
        media_type=data.get("media_type", "text"),
        external_link=data.get("external_link", ""),
        user_id=current_user.id,
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"id": post.id, "message": "created"}), 201


@api_bp.get("/events")
def list_events():
    events = Event.query.order_by(Event.starts_at.asc()).all()
    return jsonify(
        [
            {
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "starts_at": e.starts_at.isoformat(),
                "ends_at": e.ends_at.isoformat(),
                "location": e.location,
            }
            for e in events
        ]
    )
