from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    events_created = db.relationship("Event", back_populates="creator", lazy="dynamic")
    registrations_created = db.relationship(
        "Registration", back_populates="registered_by_user", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    creator = db.relationship("User", back_populates="events_created")
    registrations = db.relationship(
        "Registration",
        back_populates="event",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def registration_count(self) -> int:
        return self.registrations.count()


class Registration(db.Model):
    __tablename__ = "registrations"

    MEMBER_EXISTING = "existing"
    MEMBER_NEW = "new"
    MEMBER_TYPES = (MEMBER_EXISTING, MEMBER_NEW)

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    member_type = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    registered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    event = db.relationship("Event", back_populates="registrations")
    registered_by_user = db.relationship("User", back_populates="registrations_created")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def member_type_label(self) -> str:
        return "Existing member" if self.member_type == self.MEMBER_EXISTING else "New member"
