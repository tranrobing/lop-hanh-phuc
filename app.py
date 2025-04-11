from flask import Flask
from flask_login import LoginManager
from extensions import db  # lấy db từ extensions.py
from models import User  # import các model sau khi db được khởi tạo

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # bạn có thể lấy từ biến môi trường nếu cần
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lophanhphuc.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Thiết lập Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import route sau khi app và db được thiết lập
import auth
import attendance
import reports
