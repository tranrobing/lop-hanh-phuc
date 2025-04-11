from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import app, db
from models import User, Teacher, Student, StudentAttendance, TeacherAttendance, Shift
from sqlalchemy import func
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email
from utils import get_vietnam_time


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mật khẩu')
    remember_me = BooleanField('Lưu đăng nhập')
    submit = SubmitField('Đăng nhập')


@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect('/admin/dashboard')
        else:
            return redirect('/teacher/dashboard')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')
        
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.is_admin:
            if not password:
                flash('Yêu cầu nhập mật khẩu cho tài khoản Admin.', 'danger')
                return render_template('login.html', form=form)
                
            if check_password_hash(user.password_hash, password):
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                flash('Đăng nhập thành công!', 'success')
                return redirect(next_page or '/admin/dashboard')
            else:
                flash('Mật khẩu không đúng.', 'danger')
                
        elif user and not user.is_admin:
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Đăng nhập thành công!', 'success')
            return redirect(next_page or '/teacher/dashboard')
            
        elif not user:
            teacher = Teacher.query.filter_by(email=email).first()
            if teacher:
                new_user = User(
                    name=teacher.name,
                    email=teacher.email,
                    is_admin=False
                )
                db.session.add(new_user)
                db.session.commit()
                teacher.user_id = new_user.id
                db.session.commit()
                
                login_user(new_user, remember=form.remember_me.data)
                flash('Đăng nhập thành công!', 'success')
                return redirect('/teacher/dashboard')
            else:
                flash('Email không tồn tại trong hệ thống!', 'danger')
        else:
            flash('Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.', 'danger')
            
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất thành công!', 'success')
    return redirect('/login')


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập trang này!', 'danger')
        return redirect('/')
    
    students = Student.query.all()
    today = get_vietnam_time().date()
    
    student_attendance = {}
    for student in students:
        attendance = StudentAttendance.query.filter_by(
            student_id=student.id,
            date=today
        ).first()
        student_attendance[student.id] = attendance
    
    teacher_count_today = db.session.query(func.count(TeacherAttendance.teacher_id.distinct())).\
        filter(TeacherAttendance.date == today).scalar() or 0
    
    current_time = get_vietnam_time().time()
    current_hour = current_time.hour
    
    shifts = Shift.query.all()
    active_shifts = []
    
    for shift in shifts:
        shift_start_hour = int(shift.start_time.split(':')[0])
        shift_end_hour = int(shift.end_time.split(':')[0])
        
        if shift_start_hour <= current_hour < shift_end_hour:
            teachers_in_shift = db.session.query(Teacher).\
                join(TeacherAttendance, Teacher.id == TeacherAttendance.teacher_id).\
                filter(
                    TeacherAttendance.date == today,
                    TeacherAttendance.shift_id == shift.id
                ).all()
            
            active_shifts.append({
                'shift': shift,
                'teachers': teachers_in_shift,
                'count': len(teachers_in_shift)
            })
    
    return render_template(
        'admin/dashboard.html', 
        students=students, 
        student_attendance=student_attendance,
        today=today,
        teacher_count_today=teacher_count_today,
        active_shifts=active_shifts,
        current_time=current_time
    )


@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.is_admin:
        return redirect('/admin/dashboard')
    
    students = Student.query.all()
    today = get_vietnam_time().date()
    current_time = get_vietnam_time().time()
    current_hour = current_time.hour
    
    student_attendance = {}
    for student in students:
        attendance = StudentAttendance.query.filter_by(
            student_id=student.id,
            date=today
        ).first()
        student_attendance[student.id] = attendance
    
    teacher = None
    if hasattr(current_user, 'teacher'):
        teacher = current_user.teacher
    
    all_shifts = Shift.query.all()
    teacher_attendance = {}
    active_shifts = set()
    
    if teacher:
        attendance_records = TeacherAttendance.query.filter_by(
            teacher_id=teacher.id,
            date=today
        ).all()
        
        for record in attendance_records:
            teacher_attendance[record.shift_id] = record
    
    shifts = []
    for shift in all_shifts:
        shift_start_hour = int(shift.start_time.split(':')[0])
        shift_end_hour = int(shift.end_time.split(':')[0])
        
        if shift_start_hour <= current_hour < shift_end_hour:
            shifts.append(shift)
            active_shifts.add(shift.id)
    
    return render_template(
        'teacher/dashboard.html', 
        students=students, 
        student_attendance=student_attendance,
        teacher=teacher,
        today=today,
        shifts=shifts,
        teacher_attendance=teacher_attendance,
        active_shifts=active_shifts,
        current_time=current_time
    )
