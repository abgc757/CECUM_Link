from datetime import datetime
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class UserRole(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"
    TEACHER = "teacher"
    MODERATOR = "moderator"


class ReactionType(str, Enum):
    LIKE = "like"
    LOVE = "love"
    WOW = "wow"
    SUPPORT = "support"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, default="")
    interests = db.Column(db.Text, default="")
    profile_photo = db.Column(db.String(255), default="")
    role = db.Column(db.String(20), default=UserRole.STUDENT.value, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # posts = db.relationship("Post", backref="author", lazy=True, cascade="all, delete-orphan")
    posts = db.relationship("Post", foreign_keys="Post.user_id", backref="author", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def needs_password_setup(self) -> bool:
        return not bool(self.password_hash)

    @property
    def is_moderator(self) -> bool:
        return self.role in {UserRole.ADMIN.value, UserRole.MODERATOR.value, UserRole.TEACHER.value}

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(255), default="")
    media_type = db.Column(db.String(20), default="text")
    external_link = db.Column(db.String(255), default="")
    is_archived = db.Column(db.Boolean, default=False)
    archived_reason = db.Column(db.String(255), default="")
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    comments = db.relationship("Comment", backref="post", lazy=True, cascade="all, delete-orphan")
    reactions = db.relationship("Reaction", backref="post", lazy=True, cascade="all, delete-orphan")


class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reaction_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="uq_user_post_reaction"),)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    tagged_users = db.Column(db.String(255), default="")
    is_archived = db.Column(db.Boolean, default=False)
    archived_reason = db.Column(db.String(255), default="")
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    author = db.relationship("User", foreign_keys=[user_id])


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(150), default="")
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="")
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ConversationMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sender = db.relationship("User", foreign_keys=[sender_id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(40), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
