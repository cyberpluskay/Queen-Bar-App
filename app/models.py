from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# User model for authentication
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' or 'bartender'
    #is_active = db.Column(db.Boolean, default=True)
    

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Drink model for inventory
class Drink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)  # New cost price field

# Transaction model for grouping sales
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Track when transaction occurs

    # Relationship to track sales within this transaction (no backref here)
    #sales = db.relationship('Sale', backref='transaction', lazy=True)....REMOVE LATER i
    sales = db.relationship('Sale', backref='parent_transaction', lazy=True)
    # Total amount for this transaction
    total_amount = db.Column(db.Float, nullable=False)

# Sale model for individual items in a transaction
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drink_id = db.Column(db.Integer, db.ForeignKey('drink.id'), nullable=False)
    drink = db.relationship('Drink', backref=db.backref('sales', lazy=True))
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)

    # Link sale to a transaction (removed conflicting backref here)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    #transaction = db.relationship('Transaction', backref=db.backref('sales', lazy=True)) REMOVE LATER i

    date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

