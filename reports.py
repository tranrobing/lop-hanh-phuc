from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
import calendar
from datetime import datetime
import pytz
from sqlalchemy import func, extract

from app import db
from models import Teacher, TeacherAttendance, StudentAttendance, Student

reports_bp = Blueprint('reports', __name__)
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

@reports_bp.route('/admin/reports')
@login_required
def admin_reports():
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Get the year and month from query parameters (default to current month)
    now = datetime.now(vietnam_tz)
    year = int(request.args.get('year', now.year))
    month = int(request.args.get('month', now.month))
    
    # Get all teachers
    teachers = Teacher.query.filter_by(active=True).all()
    
    # Get the calendar for this month
    cal = calendar.monthcalendar(year, month)
    
    # Format the month name in Vietnamese
    month_names_vi = [
        "", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    month_name = month_names_vi[month]
    
    # Get total shifts and hours for each teacher
    teacher_stats = []
    
    for teacher in teachers:
        # Query for attendance records for this teacher in the selected month
        query = db.session.query(TeacherAttendance.shift_type, func.count(TeacherAttendance.id)).\
            filter(
                TeacherAttendance.teacher_id == teacher.id,
                extract('year', TeacherAttendance.date) == year,
                extract('month', TeacherAttendance.date) == month
            ).\
            group_by(TeacherAttendance.shift_type)
        
        shift_counts = dict(query.all())
        
        # Calculate totals
        total_morning = shift_counts.get('morning', 0)
        total_afternoon = shift_counts.get('afternoon', 0)
        total_1on1_1h = shift_counts.get('1on1_1h', 0)
        total_1on1_15h = shift_counts.get('1on1_1.5h', 0)
        total_1on1_2h = shift_counts.get('1on1_2h', 0)
        
        total_shifts = total_morning + total_afternoon + total_1on1_1h + total_1on1_15h + total_1on1_2h
        
        # Calculate total hours
        total_hours = (
            total_morning * 6 +  # 6 hours for morning shift
            total_afternoon * 4.75 +  # 4.75 hours for afternoon shift
            total_1on1_1h * 1 +  # 1 hour for 1on1_1h shift
            total_1on1_15h * 1.5 +  # 1.5 hours for 1on1_1.5h shift
            total_1on1_2h * 2  # 2 hours for 1on1_2h shift
        )
        
        teacher_stats.append({
            'id': teacher.id,
            'name': teacher.name,
            'total_shifts': total_shifts,
            'total_hours': total_hours,
            'morning': total_morning,
            'afternoon': total_afternoon,
            'one_on_one': total_1on1_1h + total_1on1_15h + total_1on1_2h,
            'one_on_one_1h': total_1on1_1h,
            'one_on_one_15h': total_1on1_15h, 
            'one_on_one_2h': total_1on1_2h
        })
    
    # Sort by total hours in descending order
    teacher_stats.sort(key=lambda x: x['total_hours'], reverse=True)
    
    # Get student attendance statistics
    total_students = Student.query.filter_by(active=True).count()
    student_attendance_by_day = {}
    
    for week in cal:
        for day in week:
            if day != 0:  # Skip days that belong to prev/next month
                date = datetime(year, month, day).date()
                if date.weekday() != 6:  # Skip Sundays
                    count = StudentAttendance.query.filter(
                        StudentAttendance.date == date
                    ).count()
                    student_attendance_by_day[date.strftime('%Y-%m-%d')] = {
                        'count': count,
                        'percentage': round(count / total_students * 100) if total_students > 0 else 0
                    }
    
    return render_template(
        'admin/reports.html',
        year=year,
        month=month,
        month_name=month_name,
        calendar=cal,
        teachers=teachers,
        teacher_stats=teacher_stats,
        student_attendance=student_attendance_by_day,
        total_students=total_students
    )

@reports_bp.route('/admin/reports/teacher/<int:teacher_id>')
@login_required
def teacher_detail_report(teacher_id):
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Get the year and month from query parameters (default to current month)
    now = datetime.now(vietnam_tz)
    year = int(request.args.get('year', now.year))
    month = int(request.args.get('month', now.month))
    
    # Get the teacher
    teacher = Teacher.query.get_or_404(teacher_id)
    
    # Get all attendance records for this teacher in the selected month
    attendance_records = TeacherAttendance.query.filter(
        TeacherAttendance.teacher_id == teacher.id,
        extract('year', TeacherAttendance.date) == year,
        extract('month', TeacherAttendance.date) == month
    ).order_by(TeacherAttendance.date, TeacherAttendance.time).all()
    
    # Format the month name in Vietnamese
    month_names_vi = [
        "", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    month_name = month_names_vi[month]
    
    # Group attendance records by date
    attendance_by_date = {}
    for record in attendance_records:
        date_str = record.date.strftime('%Y-%m-%d')
        if date_str not in attendance_by_date:
            attendance_by_date[date_str] = []
        
        # Format shift name in Vietnamese
        shift_vi = {
            "morning": "Sáng",
            "afternoon": "Chiều",
            "1on1_1h": "1-1 (1 giờ)",
            "1on1_1.5h": "1-1 (1.5 giờ)",
            "1on1_2h": "1-1 (2 giờ)",
        }.get(record.shift_type, record.shift_type)
        
        attendance_by_date[date_str].append({
            'id': record.id,
            'time': record.time.strftime('%H:%M'),
            'shift': shift_vi,
            'shift_type': record.shift_type
        })
    
    # Calculate summary statistics
    total_morning = sum(1 for record in attendance_records if record.shift_type == 'morning')
    total_afternoon = sum(1 for record in attendance_records if record.shift_type == 'afternoon')
    total_1on1_1h = sum(1 for record in attendance_records if record.shift_type == '1on1_1h')
    total_1on1_15h = sum(1 for record in attendance_records if record.shift_type == '1on1_1.5h')
    total_1on1_2h = sum(1 for record in attendance_records if record.shift_type == '1on1_2h')
    
    total_shifts = total_morning + total_afternoon + total_1on1_1h + total_1on1_15h + total_1on1_2h
    
    # Calculate total hours
    total_hours = (
        total_morning * 6 +  # 6 hours for morning shift
        total_afternoon * 4.75 +  # 4.75 hours for afternoon shift
        total_1on1_1h * 1 +  # 1 hour for 1on1_1h shift
        total_1on1_15h * 1.5 +  # 1.5 hours for 1on1_1.5h shift
        total_1on1_2h * 2  # 2 hours for 1on1_2h shift
    )
    
    return render_template(
        'admin/teacher_report.html',
        teacher=teacher,
        year=year,
        month=month,
        month_name=month_name,
        attendance_by_date=attendance_by_date,
        total_shifts=total_shifts,
        total_hours=total_hours,
        total_morning=total_morning,
        total_afternoon=total_afternoon,
        total_1on1=total_1on1_1h + total_1on1_15h + total_1on1_2h,
        total_1on1_1h=total_1on1_1h,
        total_1on1_15h=total_1on1_15h,
        total_1on1_2h=total_1on1_2h
    )

@reports_bp.route('/admin/reports/students')
@login_required
def student_attendance_report():
    if not current_user.is_admin:
        flash('Bạn không có quyền truy cập vào trang này.', 'danger')
        return redirect(url_for('attendance.teacher_home'))
    
    # Get the year and month from query parameters (default to current month)
    now = datetime.now(vietnam_tz)
    year = int(request.args.get('year', now.year))
    month = int(request.args.get('month', now.month))
    
    # Format the month name in Vietnamese
    month_names_vi = [
        "", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    month_name = month_names_vi[month]
    
    # Get all active students
    students = Student.query.filter_by(active=True).order_by(Student.name).all()
    
    # Get the calendar for this month
    cal = calendar.monthcalendar(year, month)
    
    # Prepare data structure for student attendance
    # For each student, we need a dict of date -> attendance status
    student_attendance = {}
    
    for student in students:
        # Get all attendance records for this student in the selected month
        attendance_records = StudentAttendance.query.filter(
            StudentAttendance.student_id == student.id,
            extract('year', StudentAttendance.date) == year,
            extract('month', StudentAttendance.date) == month
        ).all()
        
        # Create a dict of date -> attendance status
        attendance_by_date = {}
        for record in attendance_records:
            date_str = record.date.strftime('%Y-%m-%d')
            attendance_by_date[date_str] = {
                'id': record.id,
                'time': record.time.strftime('%H:%M'),
                'marked_by': record.marked_by.name
            }
        
        # Calculate total days present
        total_present = len(attendance_records)
        
        # Calculate total valid days (excluding Sundays)
        total_days = sum(1 for week in cal for day in week if day != 0 and datetime(year, month, day).weekday() != 6)
        
        student_attendance[student.id] = {
            'name': student.name,
            'attendance': attendance_by_date,
            'total_present': total_present,
            'total_days': total_days,
            'attendance_rate': round(total_present / total_days * 100) if total_days > 0 else 0
        }
    
    return render_template(
        'admin/student_report.html',
        students=students,
        student_attendance=student_attendance,
        year=year,
        month=month,
        month_name=month_name,
        calendar=cal
    )
