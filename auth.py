from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import pytz

from app import db
from models import User, Teacher, Student

auth_bp = Blueprint('auth', __name__)
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('auth.admin_dashboard'))
        else:
            return redirect(url_for('attendance.teacher_home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        # Check if this is an admin login (admin requires password)
        if password:
            user = User.query.filter_by(email=email).first()
            
            # If user exists and is admin and password is correct
            if user and user.is_admin and user.password_hash and check_password_hash(user.password_hash, password):
                login_user(user, remember=remember)
                return redirect(url_for('auth.admin_dashboard'))
            else:
                flash('Vui lòng kiểm tra lại email và mật khẩu.', 'danger')
                return redirect(url_for('auth.login'))
        else:
            # Teacher login (email only)
            teacher = Teacher.query.filter_by(email=email, active=True).first()
            if teacher:
                # Check if teacher already has a user account
                if teacher.user:
                    login_user(teacher.user, remember=remember)
                else:
                    # Create a new user for this teacher
                    new_user = User(
                        name=teacher.name,
                        email=teacher.email,
                        is_admin=False
                    )
                    db.session.add(new_user)
                    db.session.flush()  # Get ID before committing
                    
                    # Link user to teacher
                    teacher.user_id = new_user.id
                    db.session.commit()
                    
                    login_user(new_user, remember=remember)
                
                return redirect(url_for('attendance.teacher_home'))
            else:
                flash('Email không hợp lệ hoặc không được đăng ký như một giáo viên.', 'danger')
                return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất thành công.', 'success')
    return redirect(url_for('auth.login'))

# --- ADMIN ROUTES ---

@auth_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Get today's date in Vietnam timezone
    today = datetime.now(vietnam_tz).date()
    
    # Get all students who are present today
    from models import StudentAttendance
    present_students = db.session.query(StudentAttendance).filter_by(date=today).count()
    total_students = Student.query.filter_by(active=True).count()
    
    # Get currently working teachers (those who have clocked in for shifts during current time)
    from models import TeacherAttendance
    current_time = datetime.now(vietnam_tz).time()
    
    # Determine which shift applies to current time
    current_shift = None
    if current_time >= datetime.strptime('06:00', '%H:%M').time() and current_time <= datetime.strptime('12:00', '%H:%M').time():
        current_shift = 'morning'
    elif current_time >= datetime.strptime('12:01', '%H:%M').time() and current_time <= datetime.strptime('16:45', '%H:%M').time():
        current_shift = 'afternoon'
    elif current_time >= datetime.strptime('16:46', '%H:%M').time() and current_time <= datetime.strptime('21:00', '%H:%M').time():
        current_shift = '1on1%'  # Use wildcard for all 1on1 shifts
    
    if current_shift:
        if current_shift == '1on1%':
            working_teachers = db.session.query(Teacher).join(TeacherAttendance).filter(
                TeacherAttendance.date == today,
                TeacherAttendance.shift_type.like(current_shift)
            ).all()
        else:
            working_teachers = db.session.query(Teacher).join(TeacherAttendance).filter(
                TeacherAttendance.date == today,
                TeacherAttendance.shift_type == current_shift
            ).all()
    else:
        working_teachers = []
    
    return render_template(
        'admin/dashboard.html',
        present_students=present_students,
        total_students=total_students,
        working_teachers=working_teachers,
        current_shift=current_shift
    )

@auth_bp.route('/admin/teachers', methods=['GET', 'POST'])
@login_required
def manage_teachers():
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            email = request.form.get('email')
            
            # Validate input
            if not name or not email:
                flash('Vui lòng điền đầy đủ thông tin.', 'danger')
            elif Teacher.query.filter_by(email=email).first():
                flash('Email đã được sử dụng.', 'danger')
            else:
                new_teacher = Teacher(name=name, email=email)
                db.session.add(new_teacher)
                db.session.commit()
                flash(f'Đã thêm giáo viên {name} thành công.', 'success')
        
        elif action == 'edit':
            teacher_id = request.form.get('teacher_id')
            name = request.form.get('name')
            email = request.form.get('email')
            active = True if request.form.get('active') else False
            
            teacher = Teacher.query.get(teacher_id)
            if teacher:
                # Check if email is changed and already exists
                if teacher.email != email and Teacher.query.filter_by(email=email).first():
                    flash('Email đã được sử dụng.', 'danger')
                else:
                    teacher.name = name
                    teacher.email = email
                    teacher.active = active
                    
                    # Update user email if exists
                    if teacher.user:
                        teacher.user.name = name
                        teacher.user.email = email
                    
                    db.session.commit()
                    flash(f'Đã cập nhật thông tin giáo viên {name} thành công.', 'success')
            else:
                flash('Không tìm thấy giáo viên.', 'danger')
        
        elif action == 'delete':
            teacher_id = request.form.get('teacher_id')
            teacher = Teacher.query.get(teacher_id)
            
            if teacher:
                # Check if the teacher has attendance records
                if teacher.attendance_records:
                    # Just mark as inactive instead of deleting
                    teacher.active = False
                    db.session.commit()
                    flash(f'Đã vô hiệu hóa giáo viên {teacher.name}.', 'success')
                else:
                    # Delete the user if exists
                    if teacher.user:
                        db.session.delete(teacher.user)
                    
                    # Delete the teacher
                    db.session.delete(teacher)
                    db.session.commit()
                    flash('Đã xóa giáo viên thành công.', 'success')
            else:
                flash('Không tìm thấy giáo viên.', 'danger')
    
    teachers = Teacher.query.all()
    return render_template('admin/teachers.html', teachers=teachers)

@auth_bp.route('/admin/students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            
            # Validate input
            if not name:
                flash('Vui lòng nhập tên học sinh.', 'danger')
            else:
                new_student = Student(name=name)
                db.session.add(new_student)
                db.session.commit()
                flash(f'Đã thêm học sinh {name} thành công.', 'success')
        
        elif action == 'edit':
            student_id = request.form.get('student_id')
            name = request.form.get('name')
            active = True if request.form.get('active') else False
            
            student = Student.query.get(student_id)
            if student:
                student.name = name
                student.active = active
                db.session.commit()
                flash(f'Đã cập nhật thông tin học sinh {name} thành công.', 'success')
            else:
                flash('Không tìm thấy học sinh.', 'danger')
        
        elif action == 'delete':
            student_id = request.form.get('student_id')
            student = Student.query.get(student_id)
            
            if student:
                # Check if the student has attendance records
                if student.attendance_records:
                    # Just mark as inactive instead of deleting
                    student.active = False
                    db.session.commit()
                    flash(f'Đã vô hiệu hóa học sinh {student.name}.', 'success')
                else:
                    # Delete the student
                    db.session.delete(student)
                    db.session.commit()
                    flash('Đã xóa học sinh thành công.', 'success')
            else:
                flash('Không tìm thấy học sinh.', 'danger')
        
        elif action == 'upload_photo':
            student_id = request.form.get('student_id')
            student = Student.query.get(student_id)
            
            if student and 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename:
                    # In a real app, you would save the photo to a file system or cloud storage
                    # and store the URL in the database
                    # For simplicity, we'll just update a placeholder URL here
                    student.photo_url = f"/static/photos/student_{student_id}.jpg"
                    db.session.commit()
                    flash(f'Đã cập nhật ảnh cho học sinh {student.name}.', 'success')
                else:
                    flash('Không có file ảnh được chọn.', 'danger')
            else:
                flash('Không tìm thấy học sinh hoặc không có ảnh được gửi.', 'danger')
    
    # Add preset students if the table is empty
    if Student.query.count() == 0:
        preset_students = [
            "Hào", "An Nhiên", "Thiên Kim", "Thiên An", "Hải Nguyên", 
            "Tín", "Kiệt", "Duy Anh", "Ái Vy", "Hoàng Khôi", 
            "Ken", "Khải", "Phát", "Nghi"
        ]
        
        for name in preset_students:
            student = Student(name=name)
            db.session.add(student)
        
        db.session.commit()
        flash('Đã tạo danh sách học sinh mặc định.', 'success')
    
    students = Student.query.all()
    return render_template('admin/students.html', students=students)
from flask import redirect, url_for
from app import app

@app.route('/')
def index():
    # Khi người dùng truy cập trang chủ, chuyển đến trang login
    return redirect(url_for('login'))
