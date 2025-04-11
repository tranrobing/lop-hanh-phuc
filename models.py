from datetime import datetime
import pytz
from flask_login import UserMixin
from app import db

# Set timezone for Vietnam
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Only required for admin
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(vietnam_tz))
    
    # Relationship: One user can be a teacher
    teacher = db.relationship('Teacher', back_populates='user', uselist=False)
    
    def is_teacher(self):
        return self.teacher is not None

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(vietnam_tz))
    
    # Relationship: Teacher is associated with one User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', back_populates='teacher')
    
    # Relationship: Teacher can have many attendance records
    attendance_records = db.relationship('TeacherAttendance', back_populates='teacher', cascade='all, delete-orphan')

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(255), nullable=True)  # URL to stored photo
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(vietnam_tz))
    
    # Relationship: Student can have many attendance records
    attendance_records = db.relationship('StudentAttendance', back_populates='student', cascade='all, delete-orphan')

class TeacherAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)  # 'morning', 'afternoon', '1on1_1h', '1on1_1.5h', '1on1_2h'
    marked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(vietnam_tz))
    
    # Unique constraint to ensure a teacher can only clock in once per shift per day
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'date', 'shift_type', name='uix_teacher_date_shift'),
    )
    
    # Relationships
    teacher = db.relationship('Teacher', back_populates='attendance_records')
    marked_by = db.relationship('User')
    
    # For Google Sheets sync tracking
    gsheet_row_id = db.Column(db.Integer, nullable=True)  # To track which row in Google Sheets

class StudentAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(vietnam_tz))
    
    # Unique constraint to ensure a student can only be marked once per day
    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', name='uix_student_date'),
    )
    
    # Relationships
    student = db.relationship('Student', back_populates='attendance_records')
    marked_by = db.relationship('User')
    
    # For Google Sheets sync tracking
    gsheet_row_id = db.Column(db.Integer, nullable=True)  # To track which row in Google Sheets
