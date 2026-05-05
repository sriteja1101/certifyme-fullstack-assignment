from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'

    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    opportunities = db.relationship('Opportunity', backref='creator', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':        self.id,
            'full_name': self.full_name,
            'email':     self.email,
        }


class Opportunity(db.Model):
    __tablename__ = 'opportunity'

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(200), nullable=False)
    duration             = db.Column(db.String(100), nullable=False)
    start_date           = db.Column(db.String(50),  nullable=False)
    description          = db.Column(db.Text,        nullable=False)
    skills               = db.Column(db.Text,        nullable=False)   # comma-separated
    category             = db.Column(db.String(100), nullable=False)
    future_opportunities = db.Column(db.Text,        nullable=False)
    max_applicants       = db.Column(db.Integer,     nullable=True)
    created_at           = db.Column(db.DateTime,    default=datetime.utcnow)

    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)

    def to_dict(self):
        return {
            'id':                   self.id,
            'name':                 self.name,
            'duration':             self.duration,
            'start_date':           self.start_date,
            'description':          self.description,
            'skills':               [s.strip() for s in self.skills.split(',') if s.strip()],
            'category':             self.category,
            'future_opportunities': self.future_opportunities,
            'max_applicants':       self.max_applicants,
            'admin_id':             self.admin_id,
            'created_at':           self.created_at.isoformat(),
        }


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'

    id         = db.Column(db.Integer,  primary_key=True)
    admin_id   = db.Column(db.Integer,  db.ForeignKey('admin.id'), nullable=False)
    token      = db.Column(db.String(256), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean,  default=False)