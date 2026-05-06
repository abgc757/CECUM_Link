from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db, socketio
from app.models import Conversation, ConversationMember, Message

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.route("/")
@login_required
def index():
    memberships = ConversationMember.query.filter_by(user_id=current_user.id).all()
    conv_ids = [m.conversation_id for m in memberships]
    conversations = Conversation.query.filter(Conversation.id.in_(conv_ids)).all() if conv_ids else []
    selected_id = request.args.get("conversation_id", type=int)
    selected = Conversation.query.get(selected_id) if selected_id else None
    messages = Message.query.filter_by(conversation_id=selected_id).order_by(Message.sent_at.asc()).all() if selected_id else []
    return render_template("chat/index.html", conversations=conversations, selected=selected, messages=messages)


@chat_bp.route("/new-private/<int:user_id>", methods=["POST"])
@login_required
def new_private(user_id: int):
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
    content = request.form.get("content", "").strip()
    if not content:
        flash("Mensaje vacio.", "danger")
        return redirect(url_for("chat.index", conversation_id=conversation_id))
    msg = Message(conversation_id=conversation_id, sender_id=current_user.id, content=content)
    db.session.add(msg)
    db.session.commit()
    socketio.emit("new_message", {"conversation_id": conversation_id, "content": msg.content, "sender_id": current_user.id})
    return redirect(url_for("chat.index", conversation_id=conversation_id))
