"""Marshmallow schemas for request validation."""

import re

from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate, validates

from app.utils.responses import ApiError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    email = fields.String(required=True, validate=validate.Length(max=255))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8, max=128))

    @validates("email")
    def _email(self, value, **_):
        if not EMAIL_RE.match(value.strip()):
            raise ValidationError("Enter a valid email address.")

    @validates("password")
    def _password(self, value, **_):
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValidationError("Password must contain at least one letter and one number.")

    @validates("name")
    def _name(self, value, **_):
        if not value.strip():
            raise ValidationError("Name cannot be blank.")


class LoginSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    email = fields.String(required=True, validate=validate.Length(min=3, max=255))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=1, max=128))


class ProfileSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(required=True, validate=validate.Length(min=2, max=100))


class ChangePasswordSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    current_password = fields.String(required=True, validate=validate.Length(min=1, max=128))
    new_password = fields.String(required=True, validate=validate.Length(min=8, max=128))

    @validates("new_password")
    def _password(self, value, **_):
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValidationError("Password must contain at least one letter and one number.")


class AdminUserUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    is_active = fields.Boolean()
    role = fields.String(validate=validate.OneOf(["user", "admin"]))


def load_or_400(schema: Schema, payload):
    if not isinstance(payload, dict):
        raise ApiError("validation_error", "Request body must be a JSON object.", 400)
    try:
        return schema.load(payload)
    except ValidationError as e:
        raise ApiError("validation_error", "Please correct the highlighted fields.", 400, e.messages)
