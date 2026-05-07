from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import text

from app.extensions import csrf, db
from app.models import Event, Post

api_bp = Blueprint("api", __name__)


def _validate_readonly_sql(query: str):
    normalized = " ".join((query or "").strip().split())
    if not normalized:
        return "query is required"
    if ";" in normalized.rstrip(";"):
        return "only one SQL statement is allowed"
    first_word = normalized.split(" ", 1)[0].lower()
    if first_word not in {"select", "with", "pragma"}:
        return "only read-only SQL is allowed"
    forbidden = {"insert", "update", "delete", "drop", "alter", "create", "truncate", "replace"}
    lowered = normalized.lower()
    if any(token in lowered for token in forbidden):
        return "forbidden SQL keyword detected"
    return None


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


@api_bp.post("/bi/query")
@csrf.exempt
def bi_query():
    api_key = request.headers.get("X-BI-API-KEY", "")
    expected = current_app.config.get("BI_API_KEY", "")
    if not expected or api_key != expected:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    limit = int(data.get("limit", 500))
    limit = max(1, min(limit, 5000))

    err = _validate_readonly_sql(query)
    if err:
        return jsonify({"error": err}), 400

    safe_query = f"SELECT * FROM ({query}) AS q LIMIT :limit" if not query.lower().startswith("pragma") else query
    params = {"limit": limit} if "limit" in safe_query else {}
    result = db.session.execute(text(safe_query), params)
    rows = [dict(item) for item in result.mappings().all()]
    columns = list(rows[0].keys()) if rows else []
    return jsonify({"columns": columns, "rows": rows, "row_count": len(rows)})
