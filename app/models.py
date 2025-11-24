from datetime import datetime, date
from flask_login import UserMixin
from . import db, bcrypt

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add one-to-one relationship with AikidoInformation
    aikido_info = db.relationship('AikidoInformation', backref='user', uselist=False, lazy=True)
    
    # Add one-to-many relationship with TrainingAttendance
    training_sessions = db.relationship('TrainingAttendance', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class AikidoInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    aikido_type = db.Column(db.String(100), nullable=True)
    aikido_rank = db.Column(db.String(50), nullable=True)
    certificate_no = db.Column(db.String(100), nullable=True)
    afsa_no = db.Column(db.String(50), nullable=True)
    aif_no = db.Column(db.String(50), nullable=True)
    honbu_no = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., 'aikido_certificate'
    filename = db.Column(db.String(255), nullable=False)
    data = db.Column(db.Text, nullable=False)  # base64 encoded file data - supports up to 16MB
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Attachment {self.type} for user {self.user_id}>'

class TrainingAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    training_date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)  # Training hours (can be decimal like 1.5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TrainingAttendance {self.training_date} - {self.hours}h for user {self.user_id}>'

class ProofOfPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attachment_id = db.Column(db.Integer, db.ForeignKey('attachment.id'), nullable=False)
    month_year = db.Column(db.String(50), nullable=False)  # e.g., "January 2025"
    admin_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationships
    attachment = db.relationship('Attachment', backref='proof_of_payment', uselist=False)

    def __repr__(self):
        return f'<ProofOfPayment {self.month_year} for user {self.user_id} - verified: {self.admin_verified}>'

