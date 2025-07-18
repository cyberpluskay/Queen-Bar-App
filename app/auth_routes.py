from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    # If user is already logged in, redirect to their respective panel
    if current_user.is_authenticated:
        return redirect(url_for("main.admin" if current_user.role == "admin" else "main.bartender"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Login successful!", "success")

            # Handle redirect to the originally requested page
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):  # Ensure it's a safe redirect
                return redirect(next_page)

            # Redirect based on role
            return redirect(url_for("main.admin" if user.role == "admin" else "main.bartender"))

        flash("Invalid username or password", "danger")

    return render_template("login.html")


@auth.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    # Change the flash message to handle inactivity-based logouts
    flash("You have been logged out due to inactivity.", "info")
    return redirect(url_for("auth.login"))
