import os
import logging
from datetime import datetime
import pytz

from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Set up timezone
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# Set up database base class
class Base(DeclarativeBase):
    pass

# Initialize Flask app and SQLAlchemy
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-key-for-development")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database with the app
db.init_app(app)

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'

# Common context processor to add timezone info to all templates
@app.context_processor
def inject_vietnam_time():
    now = datetime.now(vietnam_tz)
    return {
        'current_datetime': now,
        'current_day': now.strftime('%Y-%m-%d'),
        'current_time': now.strftime('%H:%M'),
        'is_sunday': now.weekday() == 6  # 6 corresponds to Sunday (0 is Monday)
    }

# Load routes from modules
from auth import auth_bp
from attendance import attendance_bp
from reports import reports_bp

app.register_blueprint(auth_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(reports_bp)

# Import User model after blueprints to avoid circular imports
from models import User

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Root route redirects based on user login status and role
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('auth.admin_dashboard'))
        else:
            return redirect(url_for('attendance.teacher_home'))
    return redirect(url_for('auth.login'))

# Initialize database with app context
with app.app_context():
    import models
    db.create_all()
    
    # Create default admin user if not exists
    admin_user = db.session.query(models.User).filter_by(email='lophoanhaphanhphuc@gmail.com').first()
    if not admin_user:
        from werkzeug.security import generate_password_hash
        admin = models.User(
            name='Admin',
            email='lophoanhaphanhphuc@gmail.com',
            password_hash=generate_password_hash('4446'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        logging.info("Default admin user created")
    
    # Add preset students if the table is empty
    if models.Student.query.count() == 0:
        preset_students = [
            "Hào", "An Nhiên", "Thiên Kim", "Thiên An", "Hải Nguyên", 
            "Tín", "Kiệt", "Duy Anh", "Ái Vy", "Hoàng Khôi", 
            "Ken", "Khải", "Phát", "Nghi"
        ]
        
        for name in preset_students:
            student = models.Student(name=name)
            db.session.add(student)
        
        db.session.commit()
        logging.info("Added default student list")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
