from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

from extensions import db



class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    teacher = db.relationship('Teacher', backref='user', uselist=False)


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(255), nullable=True)

    attendance_records = db.relationship('StudentAttendance', backref='student', lazy=True)


class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    hourly_rate = db.Column(db.Float)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    attendance_records = db.relationship('TeacherAttendance', backref='teacher', lazy=True)


class StudentAttendance(db.Model):
    __tablename__ = 'student_attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.String(255))


class TeacherAttendance(db.Model):
    __tablename__ = 'teacher_attendance'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time, nullable=False)
    notes = db.Column(db.String(255))


class Shift(db.Model):
    __tablename__ = 'shifts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.Float, nullable=False)
    one_on_one = db.Column(db.Boolean, default=False)

    attendance_records = db.relationship('TeacherAttendance', backref='shift', lazy=True)
