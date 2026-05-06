from flask import Blueprint, flash, redirect, render_template, request, url_for
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
        if not user or not user.check_password(form.password.data):
            flash("Credenciales invalidas.", "danger")
            return redirect(url_for("auth.login"))
        login_user(user)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("posts.feed"))
    if request.method == "POST" and form.errors:
        flash("Revisa los datos del formulario e intenta de nuevo.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesion finalizada.", "info")
    return redirect(url_for("auth.login"))
