from datetime import datetime, timezone

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    predictions = db.relationship("Prediction", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def to_dict(self) -> dict:
        # Never include password_hash.
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": iso(self.created_at),
            "last_login_at": iso(self.last_login_at),
        }


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    disease = db.Column(db.String(20), nullable=False, index=True)
    input_data = db.Column(db.JSON, nullable=False)
    not_provided = db.Column(db.JSON, nullable=False, default=list)
    predicted_class = db.Column(db.Integer, nullable=False)
    predicted_label = db.Column(db.String(100), nullable=False)
    probability = db.Column(db.Float, nullable=True)
    risk_category = db.Column(db.String(10), nullable=True)
    model_status = db.Column(db.String(20), nullable=False)
    model_algorithm = db.Column(db.String(60), nullable=False)
    model_version = db.Column(db.String(40), nullable=False)
    factors = db.Column(db.JSON, nullable=True)
    source = db.Column(db.String(20), nullable=False, default="manual")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="predictions")

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "disease": self.disease,
            "predicted_class": self.predicted_class,
            "predicted_label": self.predicted_label,
            "probability": self.probability,
            "risk_category": self.risk_category,
            "model_status": self.model_status,
            "source": self.source,
            "created_at": iso(self.created_at),
        }

    def to_dict(self) -> dict:
        d = self.to_summary()
        d.update({
            "input_data": self.input_data,
            "not_provided": self.not_provided or [],
            "model_algorithm": self.model_algorithm,
            "model_version": self.model_version,
            "factors": self.factors,
        })
        return d


class TokenBlocklist(db.Model):
    """Revoked JWT identifiers (logout)."""

    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)


def iso(dt):
    return dt.isoformat(timespec="seconds") + "Z" if dt else None
