from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.extensions import db
from app.models import Event

events_bp = Blueprint("events", __name__, url_prefix="/events")


class EventForm(FlaskForm):
    title = StringField("Titulo", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Descripcion")
    location = StringField("Ubicacion", validators=[Length(max=150)])
    starts_at = DateTimeLocalField("Inicio", validators=[DataRequired()], format="%Y-%m-%dT%H:%M")
    ends_at = DateTimeLocalField("Fin", validators=[DataRequired()], format="%Y-%m-%dT%H:%M")
    submit = SubmitField("Crear evento")


@events_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    form = EventForm()
    if form.validate_on_submit():
        if not current_user.is_moderator:
            flash("Solo docentes/moderadores pueden crear eventos.", "danger")
            return redirect(url_for("events.index"))
        if form.ends_at.data <= form.starts_at.data:
            flash("La fecha de fin debe ser mayor a la de inicio.", "danger")
            return redirect(url_for("events.index"))
        event = Event(
            title=form.title.data.strip(),
            description=form.description.data or "",
            location=form.location.data or "",
            starts_at=form.starts_at.data,
            ends_at=form.ends_at.data,
            created_by=current_user.id,
        )
        db.session.add(event)
        db.session.commit()
        flash("Evento creado.", "success")
        return redirect(url_for("events.index"))

    upcoming = Event.query.filter(Event.ends_at >= datetime.utcnow()).order_by(Event.starts_at.asc()).all()
    return render_template("events/index.html", form=form, events=upcoming, can_create_event=current_user.is_moderator)
