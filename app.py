import os
import logging
import pytz
from datetime import datetime
from flask import Flask, g, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Bật logging để dễ debug
logging.basicConfig(level=logging.DEBUG)

# Khởi tạo timezone Việt Nam
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')


class Base(DeclarativeBase):
    pass


# Khởi tạo Flask app và database
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "lophanhphuc4446key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Cấu hình đường dẫn database từ biến môi trường
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///lophanhphuc.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Cấu hình upload ảnh
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB tối đa

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này'

# Tạo bảng và admin nếu chưa có
with app.app_context():
    from models import User, Student, Teacher, Shift
    from werkzeug.security import generate_password_hash

    db.create_all()

    # Tạo tài khoản admin mặc định nếu chưa có
    admin = User.query.filter_by(email="lophoanhaphanhphuc@gmail.com").first()
    if not admin:
        admin = User(
            name="Admin",
            email="lophoanhaphanhphuc@gmail.com",
            password_hash=generate_password_hash("4446"),
            is_admin=True
        )
        db.session.add(admin)

        # Thêm học sinh mặc định
        students = [
            "Hào", "An Nhiên", "Thiên Kim", "Thiên An", "Hải Nguyên",
            "Tín", "Kiệt", "Duy Anh", "Ái Vy", "Hoàng Khôi",
            "Ken", "Khải", "Phát", "Nghi"
        ]
        for name in students:
            student = Student(name=name)
            db.session.add(student)

        # Thêm ca mặc định
        shifts = [
            Shift(name="Sáng", start_time="06:00", end_time="12:00", duration=6),
            Shift(name="Chiều", start_time="12:00", end_time="16:45", duration=4.75),
            Shift(name="1-1 (1 giờ)", start_time="16:45", end_time="21:00", duration=1, one_on_one=True),
            Shift(name="1-1 (1.5 giờ)", start_time="16:45", end_time="21:00", duration=1.5, one_on_one=True),
            Shift(name="1-1 (2 giờ)", start_time="16:45", end_time="21:00", duration=2, one_on_one=True),
        ]
        for shift in shifts:
            db.session.add(shift)

        db.session.commit()

# Load user khi đăng nhập
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Gán thời gian Việt Nam cho mỗi request
@app.before_request
def before_request():
    g.vietnam_time = datetime.now(vietnam_tz)

# Template context – truyền hàm thời gian vào giao diện
@app.context_processor
def utility_processor():
    def get_vietnam_time():
        return datetime.now(vietnam_tz)
    return dict(get_vietnam_time=get_vietnam_time)

# Xử lý lỗi
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Import route chính
from auth import *
from attendance import *
from reports import *
