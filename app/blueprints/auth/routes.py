from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length
from sqlalchemy import or_

from app.extensions import db
from app.models import User, UserRole

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class LoginForm(FlaskForm):
    identifier = StringField("Correo o usuario", validators=[DataRequired()])
    password = PasswordField("Contrasena", validators=[DataRequired()])
    submit = SubmitField("Entrar")


class RegisterForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired(), Length(max=80)])
    email = StringField("Correo", validators=[DataRequired(), Email()])
    password = PasswordField("Contrasena", validators=[DataRequired(), Length(min=8)])
    bio = TextAreaField("Biografia")
    interests = TextAreaField("Intereses")
    submit = SubmitField("Crear cuenta")


class AdminSetupForm(FlaskForm):
    password = PasswordField("Nueva contrasena", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirmar contrasena", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Definir contrasena de administrador")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("posts.feed"))
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter((User.email == form.email.data) | (User.username == form.username.data)).first()
        if existing:
            flash("Correo o usuario ya registrado.", "danger")
            return redirect(url_for("auth.register"))
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            bio=form.bio.data or "",
            interests=form.interests.data or "",
            role=UserRole.STUDENT.value,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Cuenta creada. Ya puedes iniciar sesion.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("posts.feed"))
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data.strip()
        user = User.query.filter(
            or_(User.email == identifier.lower(), User.username == identifier)
        ).first()
        if user and user.role == UserRole.ADMIN.value and user.needs_password_setup:
            session["pending_admin_setup_user_id"] = user.id
            flash("Primer acceso del administrador: define tu contrasena.", "info")
            return redirect(url_for("auth.admin_setup"))
        if not user or not user.check_password(form.password.data):
            flash("Credenciales invalidas.", "danger")
            return redirect(url_for("auth.login"))
        login_user(user)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("posts.feed"))
    if request.method == "POST" and form.errors:
        flash("Revisa los datos del formulario e intenta de nuevo.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/admin-setup", methods=["GET", "POST"])
def admin_setup():
    if current_user.is_authenticated:
        return redirect(url_for("posts.feed"))

    pending_user_id = session.get("pending_admin_setup_user_id")
    if not pending_user_id:
        flash("No hay un proceso de configuracion de administrador en curso.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.get(pending_user_id)
    if not user or user.role != UserRole.ADMIN.value:
        session.pop("pending_admin_setup_user_id", None)
        flash("Usuario administrador no valido.", "danger")
        return redirect(url_for("auth.login"))
    if not user.needs_password_setup:
        session.pop("pending_admin_setup_user_id", None)
        flash("El administrador ya tiene contrasena configurada.", "info")
        return redirect(url_for("auth.login"))

    form = AdminSetupForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash("Las contrasenas no coinciden.", "danger")
            return redirect(url_for("auth.admin_setup"))
        user.set_password(form.password.data)
        db.session.commit()
        session.pop("pending_admin_setup_user_id", None)
        login_user(user)
        flash("Contrasena de administrador configurada correctamente.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("auth/admin_setup.html", form=form, admin_user=user)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesion finalizada.", "info")
    return redirect(url_for("auth.login"))
