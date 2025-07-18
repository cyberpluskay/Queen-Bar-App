from app import create_app, db
from app.models import User

# Create the app and start the context
app = create_app()

with app.app_context():
    # Create the admin user
    admin = User(username='admin', role='admin')
    admin.set_password('123')  # Replace with a secure password
    db.session.add(admin)

    # Create the bartender user
    bartender = User(username='bartender1', role='bartender')
    bartender.set_password('123')  # Replace with a secure password
    db.session.add(bartender)

    # Commit the users to the database
    db.session.commit()
    print("Admin and bartender users created successfully!")
