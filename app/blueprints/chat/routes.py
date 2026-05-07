from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db, socketio
from app.models import Conversation, ConversationMember, Message, User

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.route("/")
@login_required
def index():
    memberships = ConversationMember.query.filter_by(user_id=current_user.id).all()
    conv_ids = [m.conversation_id for m in memberships]
    conversations = Conversation.query.filter(Conversation.id.in_(conv_ids)).all() if conv_ids else []
    users = User.query.filter(User.id != current_user.id).order_by(User.username.asc()).all()
    selected_id = request.args.get("conversation_id", type=int)
    selected = Conversation.query.get(selected_id) if selected_id else None
    if selected and selected.id not in conv_ids:
        flash("No tienes acceso a este chat.", "danger")
        return redirect(url_for("chat.index"))
    messages = Message.query.filter_by(conversation_id=selected_id).order_by(Message.sent_at.asc()).all() if selected_id else []
    return render_template("chat/index.html", conversations=conversations, selected=selected, messages=messages, users=users)


@chat_bp.route("/new-private", methods=["POST"])
@login_required
def new_private():
    user_id = request.form.get("user_id", type=int)
    if not user_id:
        flash("Selecciona un usuario para iniciar chat privado.", "danger")
        return redirect(url_for("chat.index"))
    if user_id == current_user.id:
        flash("No puedes crear un chat privado contigo mismo.", "danger")
        return redirect(url_for("chat.index"))
    other_user = User.query.get_or_404(user_id)
    existing = (
        db.session.query(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .filter(Conversation.is_group.is_(False))
        .group_by(Conversation.id)
        .having(db.func.count(ConversationMember.id) == 2)
        .all()
    )
    for conv_candidate in existing:
        members = ConversationMember.query.filter_by(conversation_id=conv_candidate.id).all()
        member_ids = {m.user_id for m in members}
        if member_ids == {current_user.id, other_user.id}:
            return redirect(url_for("chat.index", conversation_id=conv_candidate.id))

    conv = Conversation(name="", is_group=False)
    db.session.add(conv)
    db.session.flush()
    db.session.add(ConversationMember(conversation_id=conv.id, user_id=current_user.id))
    db.session.add(ConversationMember(conversation_id=conv.id, user_id=user_id))
    db.session.commit()
    return redirect(url_for("chat.index", conversation_id=conv.id))


@chat_bp.route("/send/<int:conversation_id>", methods=["POST"])
@login_required
def send_message(conversation_id: int):
    membership = ConversationMember.query.filter_by(conversation_id=conversation_id, user_id=current_user.id).first()
    if not membership:
        flash("No tienes acceso a este chat.", "danger")
        return redirect(url_for("chat.index"))
    content = request.form.get("content", "").strip()
    if not content:
        flash("Mensaje vacio.", "danger")
        return redirect(url_for("chat.index", conversation_id=conversation_id))
    msg = Message(conversation_id=conversation_id, sender_id=current_user.id, content=content)
    db.session.add(msg)
    db.session.commit()
    socketio.emit("new_message", {"conversation_id": conversation_id, "content": msg.content, "sender_id": current_user.id})
    return redirect(url_for("chat.index", conversation_id=conversation_id))


@chat_bp.route("/new-group", methods=["POST"])
@login_required
def new_group():
    name = request.form.get("name", "").strip()
    member_ids = request.form.getlist("member_ids")
    parsed_ids = set()
    for value in member_ids:
        try:
            uid = int(value)
            if uid != current_user.id:
                parsed_ids.add(uid)
        except (TypeError, ValueError):
            continue

    if len(parsed_ids) < 1:
        flash("Selecciona al menos un usuario para crear el chat grupal.", "danger")
        return redirect(url_for("chat.index"))

    conv = Conversation(name=name or "Grupo", is_group=True)
    db.session.add(conv)
    db.session.flush()

    db.session.add(ConversationMember(conversation_id=conv.id, user_id=current_user.id))
    for uid in parsed_ids:
        if User.query.get(uid):
            db.session.add(ConversationMember(conversation_id=conv.id, user_id=uid))
    db.session.commit()
    flash("Chat grupal creado.", "success")
    return redirect(url_for("chat.index", conversation_id=conv.id))
