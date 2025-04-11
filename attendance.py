from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import calendar
import pytz

from app import db
from models import Teacher, Student, TeacherAttendance, StudentAttendance
from gsheet import add_attendance_to_sheet, delete_attendance_from_sheet

attendance_bp = Blueprint('attendance', __name__)
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

@attendance_bp.route('/teacher/home')
@login_required
def teacher_home():
    if current_user.is_admin:
        return redirect(url_for('auth.admin_dashboard'))
    
    # Get the current date and time in Vietnam timezone
    now = datetime.now(vietnam_tz)
    today = now.date()
    current_time = now.time()
    
    # Check if today is Sunday (weekday() returns 6 for Sunday)
    is_sunday = now.weekday() == 6
    
    # Get the teacher associated with the current user
    teacher = None
    if current_user.teacher:
        teacher = current_user.teacher
    else:
        flash('Không tìm thấy thông tin giáo viên. Vui lòng liên hệ quản trị viên.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Determine which shift buttons to show
    show_morning = (
        not is_sunday and
        current_time >= datetime.strptime('06:00', '%H:%M').time() and 
        current_time <= datetime.strptime('12:00', '%H:%M').time()
    )
    
    show_afternoon = (
        not is_sunday and
        current_time >= datetime.strptime('12:00', '%H:%M').time() and 
        current_time <= datetime.strptime('16:45', '%H:%M').time()
    )
    
    show_1on1 = (
        not is_sunday and
        current_time >= datetime.strptime('16:45', '%H:%M').time() and 
        current_time <= datetime.strptime('21:00', '%H:%M').time()
    )
    
    # Check if teacher has already clocked in for any shift today
    morning_attended = db.session.query(TeacherAttendance).filter_by(
        teacher_id=teacher.id, 
        date=today,
        shift_type='morning'
    ).first() is not None
    
    afternoon_attended = db.session.query(TeacherAttendance).filter_by(
        teacher_id=teacher.id, 
        date=today,
        shift_type='afternoon'
    ).first() is not None
    
    oneon1_1h_attended = db.session.query(TeacherAttendance).filter_by(
        teacher_id=teacher.id, 
        date=today,
        shift_type='1on1_1h'
    ).first() is not None
    
    oneon1_15h_attended = db.session.query(TeacherAttendance).filter_by(
        teacher_id=teacher.id, 
        date=today,
        shift_type='1on1_1.5h'
    ).first() is not None
    
    oneon1_2h_attended = db.session.query(TeacherAttendance).filter_by(
        teacher_id=teacher.id, 
        date=today,
        shift_type='1on1_2h'
    ).first() is not None
    
    # Get all active students with their attendance status for today
    students_with_status = []
    active_students = Student.query.filter_by(active=True).all()
    
    for student in active_students:
        attendance = StudentAttendance.query.filter_by(
            student_id=student.id, 
            date=today
        ).first()
        
        students_with_status.append({
            'student': student,
            'present': attendance is not None
        })
    
    # Generate calendar data for the current month
    cal_year = now.year
    cal_month = now.month
    
    # Get the calendar for this month
    cal = calendar.monthcalendar(cal_year, cal_month)
    
    # Get all teacher attendance records for this month
    first_day = datetime(cal_year, cal_month, 1).date()
    last_day = datetime(cal_year, cal_month, calendar.monthrange(cal_year, cal_month)[1]).date()
    
    attendance_records = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher.id,
        TeacherAttendance.date >= first_day,
        TeacherAttendance.date <= last_day
    ).all()
    
    # Create a dict to easily look up attendance by date
    attendance_by_date = {}
    for record in attendance_records:
        date_str = record.date.strftime('%Y-%m-%d')
        if date_str not in attendance_by_date:
            attendance_by_date[date_str] = []
        attendance_by_date[date_str].append(record.shift_type)
    
    # Calculate summary statistics
    total_morning = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher.id,
        TeacherAttendance.date >= first_day,
        TeacherAttendance.date <= last_day,
        TeacherAttendance.shift_type == 'morning'
    ).count()
    
    total_afternoon = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher.id,
        TeacherAttendance.date >= first_day,
        TeacherAttendance.date <= last_day,
        TeacherAttendance.shift_type == 'afternoon'
    ).count()
    
    total_1on1_1h = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher.id,
        TeacherAttendance.date >= first_day,
        TeacherAttendance.date <= last_day,
        TeacherAttendance.shift_type == '1on1_1h'
    ).count()
    
    total_1on1_15h = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher.id,
        TeacherAttendance.date >= first_day,
        TeacherAttendance.date <= last_day,
        TeacherAttendance.shift_type == '1on1_1.5h'
    ).count()
    
    total_1on1_2h = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher.id,
        TeacherAttendance.date >= first_day,
        TeacherAttendance.date <= last_day,
        TeacherAttendance.shift_type == '1on1_2h'
    ).count()
    
    # Calculate total hours
    total_hours = (
        total_morning * 6 +  # 6 hours for morning shift
        total_afternoon * 4.75 +  # 4.75 hours for afternoon shift
        total_1on1_1h * 1 +  # 1 hour for 1on1_1h shift
        total_1on1_15h * 1.5 +  # 1.5 hours for 1on1_1.5h shift
        total_1on1_2h * 2  # 2 hours for 1on1_2h shift
    )
    
    # Format the month name in Vietnamese
    month_names_vi = [
        "", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    month_name = month_names_vi[cal_month]
    
    return render_template(
        'teacher/home.html',
        teacher=teacher,
        show_morning=show_morning,
        show_afternoon=show_afternoon,
        show_1on1=show_1on1,
        morning_attended=morning_attended,
        afternoon_attended=afternoon_attended,
        oneon1_1h_attended=oneon1_1h_attended,
        oneon1_15h_attended=oneon1_15h_attended,
        oneon1_2h_attended=oneon1_2h_attended,
        students=students_with_status,
        calendar=cal,
        today=today,
        attendance_by_date=attendance_by_date,
        total_morning=total_morning,
        total_afternoon=total_afternoon,
        total_1on1=total_1on1_1h + total_1on1_15h + total_1on1_2h,
        total_hours=total_hours,
        year=cal_year,
        month=cal_month,
        month_name=month_name,
        is_sunday=is_sunday
    )

@attendance_bp.route('/teacher/clock-in', methods=['POST'])
@login_required
def teacher_clock_in():
    if current_user.is_admin:
        flash('Quản trị viên không thể chấm công.', 'danger')
        return redirect(url_for('auth.admin_dashboard'))
    
    # Get the current date and time in Vietnam timezone
    now = datetime.now(vietnam_tz)
    today = now.date()
    current_time = now.time()
    
    # Check if today is Sunday
    if now.weekday() == 6:
        flash('Không thể chấm công vào Chủ Nhật.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Get the shift type from the form
    shift_type = request.form.get('shift_type')
    valid_shift_types = ['morning', 'afternoon', '1on1_1h', '1on1_1.5h', '1on1_2h']
    
    if shift_type not in valid_shift_types:
        flash('Loại ca không hợp lệ.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Validate if the current time is within the allowed range for the selected shift
    if shift_type == 'morning' and (
        current_time < datetime.strptime('06:00', '%H:%M').time() or 
        current_time > datetime.strptime('12:00', '%H:%M').time()
    ):
        flash('Không thể chấm công ca sáng ngoài giờ quy định (06:00 - 12:00).', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    if shift_type == 'afternoon' and (
        current_time < datetime.strptime('12:00', '%H:%M').time() or 
        current_time > datetime.strptime('16:45', '%H:%M').time()
    ):
        flash('Không thể chấm công ca chiều ngoài giờ quy định (12:00 - 16:45).', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    if shift_type.startswith('1on1') and (
        current_time < datetime.strptime('16:45', '%H:%M').time() or 
        current_time > datetime.strptime('21:00', '%H:%M').time()
    ):
        flash('Không thể chấm công ca 1-1 ngoài giờ quy định (16:45 - 21:00).', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Check if teacher has already clocked in for this shift today
    teacher = current_user.teacher
    existing_record = TeacherAttendance.query.filter_by(
        teacher_id=teacher.id,
        date=today,
        shift_type=shift_type
    ).first()
    
    if existing_record:
        flash(f'Bạn đã chấm công cho ca này hôm nay rồi.', 'warning')
        return redirect(url_for('attendance.teacher_home'))
    
    # Create new attendance record
    attendance_record = TeacherAttendance(
        teacher_id=teacher.id,
        date=today,
        time=current_time,
        shift_type=shift_type,
        marked_by_id=current_user.id
    )
    
    db.session.add(attendance_record)
    db.session.flush()  # Get ID without committing
    
    try:
        # Add to Google Sheet
        row_id = add_attendance_to_sheet(
            date=today.strftime('%Y-%m-%d'),
            time=current_time.strftime('%H:%M'),
            name=teacher.name,
            status="Có mặt",
            shift=shift_type,
            marked_by=current_user.name,
            is_student=False
        )
        
        # Save the Google Sheet row ID if available
        if row_id:
            attendance_record.gsheet_row_id = row_id
        
        db.session.commit()
        
        flash(f'Đã chấm công thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Đã xảy ra lỗi: {str(e)}', 'danger')
    
    return redirect(url_for('attendance.teacher_home'))

@attendance_bp.route('/student/mark-attendance', methods=['POST'])
@login_required
def mark_student_attendance():
    # Get the current date and time in Vietnam timezone
    now = datetime.now(vietnam_tz)
    today = now.date()
    current_time = now.time()
    
    # Check if today is Sunday
    if now.weekday() == 6:
        flash('Không thể điểm danh vào Chủ Nhật.', 'danger')
        return redirect(url_for('attendance.teacher_home' if not current_user.is_admin else 'auth.admin_dashboard'))
    
    # Get student ID from form
    student_id = request.form.get('student_id')
    student = Student.query.get(student_id)
    
    if not student:
        flash('Không tìm thấy học sinh.', 'danger')
        return redirect(url_for('attendance.teacher_home' if not current_user.is_admin else 'auth.admin_dashboard'))
    
    # Check if student has already been marked today
    existing_record = StudentAttendance.query.filter_by(
        student_id=student.id,
        date=today
    ).first()
    
    if existing_record:
        flash(f'Học sinh {student.name} đã được điểm danh hôm nay rồi.', 'warning')
        return redirect(url_for('attendance.teacher_home' if not current_user.is_admin else 'auth.admin_dashboard'))
    
    # Create new attendance record
    attendance_record = StudentAttendance(
        student_id=student.id,
        date=today,
        time=current_time,
        marked_by_id=current_user.id
    )
    
    db.session.add(attendance_record)
    db.session.flush()  # Get ID without committing
    
    try:
        # Add to Google Sheet
        row_id = add_attendance_to_sheet(
            date=today.strftime('%Y-%m-%d'),
            time=current_time.strftime('%H:%M'),
            name=student.name,
            status="Có mặt",
            shift="Học sinh",
            marked_by=current_user.name,
            is_student=True
        )
        
        # Save the Google Sheet row ID if available
        if row_id:
            attendance_record.gsheet_row_id = row_id
        
        db.session.commit()
        
        flash(f'Đã điểm danh học sinh {student.name} thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Đã xảy ra lỗi: {str(e)}', 'danger')
    
    return redirect(url_for('attendance.teacher_home' if not current_user.is_admin else 'auth.admin_dashboard'))

@attendance_bp.route('/admin/delete-attendance', methods=['POST'])
@login_required
def delete_attendance():
    if not current_user.is_admin:
        flash('Bạn không có quyền thực hiện thao tác này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    attendance_type = request.form.get('type')  # 'teacher' or 'student'
    attendance_id = request.form.get('id')
    
    if attendance_type == 'teacher':
        attendance = TeacherAttendance.query.get(attendance_id)
    else:
        attendance = StudentAttendance.query.get(attendance_id)
    
    if not attendance:
        flash('Không tìm thấy bản ghi điểm danh.', 'danger')
        return redirect(url_for('auth.admin_dashboard'))
    
    # Delete from Google Sheet if row_id exists
    if attendance.gsheet_row_id:
        try:
            delete_attendance_from_sheet(attendance.gsheet_row_id)
        except Exception as e:
            flash(f'Lỗi khi xóa từ Google Sheet: {str(e)}', 'warning')
    
    # Delete from database
    db.session.delete(attendance)
    db.session.commit()
    
    flash('Đã xóa bản ghi điểm danh thành công.', 'success')
    return redirect(url_for('auth.admin_dashboard'))

@attendance_bp.route('/admin/attendance/today')
@login_required
def admin_attendance_today():
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Get today's date in Vietnam timezone
    today = datetime.now(vietnam_tz).date()
    
    # Get all teacher attendance records for today
    teacher_records = TeacherAttendance.query.filter_by(date=today).all()
    
    # Get all student attendance records for today
    student_records = StudentAttendance.query.filter_by(date=today).all()
    
    return render_template(
        'admin/attendance_today.html',
        teacher_records=teacher_records,
        student_records=student_records,
        today=today
    )
