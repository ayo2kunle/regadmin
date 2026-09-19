import json
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


def utcnow():
    return datetime.now(timezone.utc)


class Tenant(db.Model):
    """An organization subscribed to RegAdmin."""

    __tablename__ = "tenants"

    PLAN_STARTER = "starter"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(12), unique=True, nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    plan = db.Column(db.String(40), nullable=False, default=PLAN_STARTER)
    subscription_status = db.Column(db.String(20), nullable=False, default="active")
    is_founding = db.Column(db.Boolean, nullable=False, default=False)
    logo = db.Column(db.LargeBinary, nullable=True)
    logo_mime = db.Column(db.String(80), nullable=True)
    logo_in_header = db.Column(db.Boolean, nullable=False, default=True)
    logo_on_public = db.Column(db.Boolean, nullable=False, default=True)
    logo_on_qr = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    users = db.relationship("User", back_populates="tenant", lazy="dynamic")
    events = db.relationship("Event", back_populates="tenant", lazy="dynamic")
    addresses = db.relationship(
        "Address", back_populates="tenant", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def has_logo(self) -> bool:
        return bool(self.logo)

    def shows_logo(self, place: str) -> bool:
        return self.has_logo and bool(getattr(self, place))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=True, index=True)
    is_platform_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_tenant_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="users")
    events_created = db.relationship("Event", back_populates="creator", lazy="dynamic")
    registrations_created = db.relationship(
        "Registration", back_populates="registered_by_user", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self) -> str:
        return self.name or self.username


class TenantApplication(db.Model):
    """Signup request. A tenant is created only after a platform admin approves it."""

    __tablename__ = "tenant_applications"

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    id = db.Column(db.Integer, primary_key=True)
    applicant_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    organization_name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])


class Address(db.Model):
    """A street address saved for an organization and reused on events."""

    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    street = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(120), nullable=False, default="")
    state_code = db.Column(db.String(20), nullable=False, default="")
    state_name = db.Column(db.String(120), nullable=False, default="")
    country_code = db.Column(db.String(2), nullable=False)
    country_name = db.Column(db.String(120), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="addresses")
    events = db.relationship("Event", back_populates="address", lazy="dynamic")

    @property
    def one_line(self) -> str:
        locality = " ".join(part for part in (self.city, self.state_name, self.postal_code) if part)
        parts = [self.street, locality, self.country_name]
        return ", ".join(part for part in parts if part)


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(12), unique=True, nullable=True, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(255), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey("addresses.id"), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    field_config = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.LargeBinary, nullable=True)
    cover_mime = db.Column(db.String(80), nullable=True)
    cover_x = db.Column(db.Float, nullable=False, default=50)
    cover_y = db.Column(db.Float, nullable=False, default=50)
    cover_scale = db.Column(db.Float, nullable=False, default=1)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="events")
    address = db.relationship("Address", back_populates="events")
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

    @property
    def settings(self):
        from app.fields import parse_stored_config

        return parse_stored_config(self.field_config)

    @property
    def has_cover(self) -> bool:
        return bool(self.cover_image)

    @property
    def place_line(self) -> str:
        if self.address:
            return f"{self.venue} · {self.address.one_line}"
        return self.venue


class Registration(db.Model):
    __tablename__ = "registrations"

    MEMBER_EXISTING = "existing"
    MEMBER_NEW = "new"
    MEMBER_TYPES = (MEMBER_EXISTING, MEMBER_NEW)

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, default="")
    phone = db.Column(db.String(40), nullable=True)
    member_type = db.Column(db.String(20), nullable=False, default="")
    notes = db.Column(db.Text, nullable=True)
    custom_data = db.Column(db.Text, nullable=True)
    self_registered = db.Column(db.Boolean, nullable=False, default=False)
    registered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    event = db.relationship("Event", back_populates="registrations")
    registered_by_user = db.relationship("User", back_populates="registrations_created")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def member_type_label(self) -> str:
        if self.member_type == self.MEMBER_EXISTING:
            return "Existing member"
        if self.member_type == self.MEMBER_NEW:
            return "New member"
        return ""

    @property
    def custom_values(self) -> dict:
        if not self.custom_data:
            return {}
        try:
            loaded = json.loads(self.custom_data)
        except (TypeError, json.JSONDecodeError):
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def column_value(self, key: str) -> str:
        if key == "first_name":
            return self.first_name
        if key == "last_name":
            return self.last_name
        if key == "email":
            return self.email or "—"
        if key == "phone":
            return self.phone or "—"
        if key == "member_type":
            return self.member_type_label or "—"
        if key == "notes":
            return self.notes or "—"
        if key == "registered_by":
            if self.self_registered:
                return "Guest"
            if self.registered_by_user:
                return self.registered_by_user.display_name
            return "—"
        return self.custom_values.get(key) or "—"
