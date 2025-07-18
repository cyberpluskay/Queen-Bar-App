from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'

    # Ensure the database is created in the root folder
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.getcwd(), "database.db")}'

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # 🚀 Add this line to redirect users to login if they are not authenticated
    login_manager.login_view = "auth.login"

    # Register Blueprints
    from app.routes import main
    from app.auth_routes import auth
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix="/auth")  # Authentication routes under /auth

    return app

# User loader function for Flask-Login
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
