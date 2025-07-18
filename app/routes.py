from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from app.models import Drink, Sale, Transaction, User
from app.forms import AddDrinkForm
from app import db
from datetime import datetime
import csv
from io import BytesIO
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sys
sys.path.append("..")

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html', title="Home")

from flask_login import login_required, current_user


# this is the admin route

@main.route('/admin', methods=['GET', 'POST'])
@login_required  # Requires login
def admin():
    if current_user.role != 'admin':  # Restrict access to admins only
        flash('Access Denied! Only admins can view this page.', 'danger')
        return redirect(url_for('main.bartender'))  # Redirect bartenders

    form = AddDrinkForm()
    low_stock_drinks = []
    if form.validate_on_submit():
        cost_price = request.form.get('cost_price', type=float)  # Get the cost price from the form

        # **Check if the drink name already exists**
        existing_drink = Drink.query.filter_by(name=form.name.data).first()
        if existing_drink:
            flash(f'Drink with the name "{form.name.data}" already exists!', 'danger')
            return redirect(url_for('main.admin'))

        # **Create and add the new drink**
        new_drink = Drink(
            name=form.name.data,
            price=form.price.data,
            quantity=form.quantity.data,
            cost_price=cost_price  # Add cost_price
        )
        db.session.add(new_drink)
        db.session.commit()
        flash("Drink added successfully!", "success")
        return redirect(url_for("main.admin"))


    # Fetch all drinks from the database
    drinks = Drink.query.all()

    # Check low-stock levels
    if request.method == 'POST' and 'check_low_stock' in request.form:
        low_stock_drinks = [drink for drink in drinks if drink.quantity < 10]
        if not low_stock_drinks:
            flash('All drinks are sufficiently stocked!', 'info')

    return render_template('admin.html', title="Admin Panel", form=form, drinks=drinks, low_stock_drinks=low_stock_drinks)

@main.route('/edit_drink/<int:drink_id>', methods=['GET', 'POST'])
def edit_drink(drink_id):
    drink = Drink.query.get_or_404(drink_id)
    if request.method == 'POST':
        # Update the drink details
        drink.name = request.form['name']
        drink.price = float(request.form['price'])
        drink.quantity = int(request.form['quantity'])
        drink.cost_price = request.form.get('cost_price', type=float)
        db.session.commit()
        flash('Drink updated successfully!', 'success')
        return redirect(url_for('main.admin'))

    return render_template('edit_drink.html', title="Edit Drink", drink=drink)

@main.route('/delete_drink/<int:drink_id>', methods=['POST'])
def delete_drink(drink_id):
    drink = Drink.query.get_or_404(drink_id)
    db.session.delete(drink)
    db.session.commit()
    flash('Drink deleted successfully!', 'success')
    return redirect(url_for('main.admin'))

@main.route('/sales_management', methods=['GET'])
def sales_management():
    sales = Sale.query.order_by(Sale.date.desc()).all()
    return render_template('sales_management.html', title="Sales Management", sales=sales)

@main.route('/edit_sale/<int:sale_id>', methods=['GET', 'POST'])
def edit_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    drinks = Drink.query.all()

    if request.method == 'POST':
        original_drink = Drink.query.get(sale.drink_id)
        original_drink.quantity += sale.quantity

        sale.drink_id = int(request.form['drink_id'])
        sale.quantity = int(request.form['quantity'])
        new_drink = Drink.query.get(sale.drink_id)

        if new_drink.quantity < sale.quantity:
            flash('Not enough stock available for the selected drink!', 'danger')
            return redirect(url_for('main.edit_sale', sale_id=sale.id))

        new_drink.quantity -= sale.quantity
        sale.total_price = sale.quantity * new_drink.price
        db.session.commit()
        flash('Sale updated successfully!', 'success')
        return redirect(url_for('main.sales_management'))

    return render_template('edit_sale.html', title="Edit Sale", sale=sale, drinks=drinks)

# this will show a delete message 
#@main.route('/delete_drink/<int:drink_id>', methods=['POST'])
#def delete_drink(drink_id):
    # Instead of deleting, show a message
 #   flash("Sorry, you cannot delete this drink as it is needed for reporting purposes.", "danger")
  #  return redirect(url_for('main.admin'))

@main.route('/delete_sale/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    drink = Drink.query.get(sale.drink_id)
    drink.quantity += sale.quantity
    db.session.delete(sale)
    db.session.commit()
    flash('Sale deleted successfully!', 'success')
    return redirect(url_for('main.sales_management'))

# Bartender route

@main.route('/bartender', methods=['GET', 'POST'])
@login_required
def bartender():
    if request.method == 'POST':
        # Retrieve and process multiple drinks
        drink_ids = request.form.getlist('drink_id[]')
        quantities = request.form.getlist('quantity[]')

        total_amount = 0  # Initialize total transaction amount

        for i in range(len(drink_ids)):
            drink = Drink.query.get_or_404(int(drink_ids[i]))
            quantity_sold = int(quantities[i])

            # Check stock availability
            if drink.quantity < quantity_sold:
                flash(f'Not enough stock for {drink.name}!', 'danger')
                db.session.rollback()
                return redirect(url_for('main.bartender'))

            # Calculate total amount for the transaction
            total_amount += quantity_sold * drink.price

        # Create the transaction and commit it to get its ID
        transaction = Transaction(user_id=current_user.id, total_amount=total_amount)
        db.session.add(transaction)
        db.session.flush()  # Flush to get transaction.id without full commit yet

        # Add the individual sales and reduce drink stock
        for i in range(len(drink_ids)):
            drink = Drink.query.get_or_404(int(drink_ids[i]))
            quantity_sold = int(quantities[i])

            # Calculate profit per sale
            sale_total = quantity_sold * drink.price
            profit = (drink.price - drink.cost_price) * quantity_sold

            # Record sale and update stock
            sale = Sale(
                drink_id=drink.id,
                quantity=quantity_sold,
                total_price=sale_total,
                profit=profit,  # Track profit per sale
                transaction_id=transaction.id,  # Use the flushed transaction.id
                date=datetime.now()
            )
            drink.quantity -= quantity_sold
            db.session.add(sale)

        # Final commit after adding sales
        db.session.commit()
        flash('Drinks sold successfully!', 'success')
        return redirect(url_for('main.bartender'))

    # Fetch drinks for sale
    drinks = Drink.query.all()

    # Fetch today's sales for the summary section
    today = datetime.today().date()
    today_sales = Sale.query.join(Transaction).filter(db.func.date(Sale.date) == today).all()
    total_daily_sales = sum(sale.total_price for sale in today_sales)
    total_items_sold = sum(sale.quantity for sale in today_sales)

    return render_template(
        'bartender.html',
        title="Bartender Panel",
        drinks=drinks,
        today_sales=today_sales,
        total_daily_sales=total_daily_sales,
        total_items_sold=total_items_sold
    )





# DASHBOard
@main.route('/dashboard', methods=['GET'])
@login_required  # Requires login
def dashboard():
    total_revenue = db.session.query(db.func.sum(Sale.total_price)).scalar() or 0
    total_drinks_sold = db.session.query(db.func.sum(Sale.quantity)).scalar() or 0
    low_stock_count = Drink.query.filter(Drink.quantity < 10).count()
    total_drinks_available = Drink.query.count()

    return render_template(
        'dashboard.html',
        title="Dashboard Overview",
        total_revenue=total_revenue,
        total_drinks_sold=total_drinks_sold,
        low_stock_count=low_stock_count,
        total_drinks_available=total_drinks_available
    )

@main.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.bartender'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for('main.create_user'))
        
        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("User created successfully!", "success")
        return redirect(url_for('main.admin'))
    
    return render_template('create_user.html', title="Create User")

@main.route('/manage_users', methods=['GET'])
@login_required
def manage_users():
    if current_user.role != "admin":  # Restrict to admins only
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.bartender'))

    users = User.query.all()  # Fetch all users
    return render_template('manage_users.html', title="Manage Users", users=users)

@main.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.bartender'))

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.username = request.form["username"]
        user.role = request.form["role"]
        db.session.commit()
        flash("User updated successfully!", "success")
        return redirect(url_for('main.manage_users'))

    return render_template('edit_user.html', title="Edit User", user=user)

@main.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.bartender'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for('main.manage_users'))

#Sales report route
@main.route('/sales_report_by_user', methods=['GET'])
@login_required
def sales_report_by_user():
    if current_user.role != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.bartender'))

    # Get all users who have made sales
    users = User.query.join(Sale).all()

    return render_template('sales_report_by_user.html', title="Sales Report by User", users=users)

#detailed sales details starts here

@main.route('/user_sales_detail/<int:user_id>', methods=['GET'])
@login_required
def user_sales_detail(user_id):
    user = User.query.get_or_404(user_id)

    # Fetch sales linked to the user’s transactions
    sales = Sale.query.join(Transaction).filter(Transaction.user_id == user.id).all()

    # Prepare sales data
    sales_data = [
        {
            'drink_name': sale.drink.name if sale.drink else 'Unknown Drink',
            'quantity': sale.quantity,
            'total_price': sale.total_price,
            'date': sale.date.strftime('%Y-%m-%d %H:%M:%S')
        }
        for sale in sales
    ]

    return render_template(
        'user_sales_detail.html',
        title=f"{user.username}'s Sales",
        user=user,
        sales=sales_data
    )
# user sales deatials ends here 


# Daily sales Report route 

import csv
from flask import make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Daily Sales Report Route with Date Range, User, and Drink Filters ,its exports are down here 

@main.route('/daily_sales_report', methods=['GET', 'POST'])
@login_required
def daily_sales_report():
    start_date = None
    end_date = None
    selected_user = None
    selected_drink = None
    total_revenue = 0
    total_drinks_sold = 0
    sales_data = []

    # Get users and drinks for the form
    users = User.query.all()
    drinks = Drink.query.all()

    if request.method == 'POST':
        # Get filters from the form
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        selected_user = request.form.get('user_filter')
        selected_drink = request.form.get('drink_filter')

        # Convert dates to datetime objects
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')

        # Build query with filters
        query = Sale.query.filter(
            db.func.date(Sale.date) >= start_date_obj.date(),
            db.func.date(Sale.date) <= end_date_obj.date()
        )

        if selected_user:
            query = query.filter(Sale.user_id == int(selected_user))
        
        if selected_drink:
            query = query.filter(Sale.drink_id == int(selected_drink))
        
        sales = query.all()

        # Calculate total revenue and drinks sold
        total_revenue = sum(sale.total_price for sale in sales)
        total_drinks_sold = sum(sale.quantity for sale in sales)

        # Prepare data for the table
        sales_data = [
            {
                'drink_name': sale.drink.name if sale.drink else 'Unknown Drink',
                'quantity_sold': sale.quantity,
                'total_price': sale.total_price,
                'time': sale.date.strftime('%H:%M:%S'),
                'date': sale.date.strftime('%Y-%m-%d')
            }
            for sale in sales
        ]

        # Handle CSV and PDF export
        if 'export_csv' in request.form:
            return export_sales_to_csv(sales_data)
        elif 'export_pdf' in request.form:
            return export_sales_to_pdf(sales_data)

        if not sales_data:
            flash("No sales recorded within the selected range.", "info")

    return render_template(
        'daily_sales_report.html',
        title="Daily Sales Report",
        start_date=start_date,
        end_date=end_date,
        selected_user=selected_user,
        selected_drink=selected_drink,
        users=users,
        drinks=drinks,
        total_revenue=total_revenue,
        total_drinks_sold=total_drinks_sold,
        sales_data=sales_data
    )

# This is to export sales reports 
def export_sales_to_csv(sales):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Drink', 'Quantity Sold', 'Total Price (₵)', 'Time', 'Date'])
    for sale in sales:
        writer.writerow([
            sale['drink_name'],
            sale['quantity_sold'],
            f'₵{sale["total_price"]}',
            sale['time'],
            sale['date']
        ])
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=daily_sales_report.csv"}
    )


def export_sales_to_pdf(sales):
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf.setTitle("Daily Sales Report")

    y_position = 750
    pdf.drawString(30, y_position, "Daily Sales Report")
    y_position -= 30
    pdf.drawString(30, y_position, "Drink Name      Quantity      Total Price      Time      Date")
    y_position -= 20

    for sale in sales:
        pdf.drawString(30, y_position, f"{sale['drink_name']}      {sale['quantity_sold']}      ₵{sale['total_price']}      {sale['time']}      {sale['date']}")
        y_position -= 20
        if y_position < 50:
            pdf.showPage()
            y_position = 750

    pdf.save()
    pdf_buffer.seek(0)
    return Response(
        pdf_buffer,
        mimetype='application/pdf',
        headers={"Content-Disposition": "attachment;filename=daily_sales_report.pdf"}
    )



# Low Stock levels report
# Route to view and export low stock drinks with live report
@main.route('/low_stock_report', methods=['GET', 'POST'])
@login_required
def low_stock_report():
    if current_user.role != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.bartender'))
    
    reorder_threshold = 10  # Default threshold
    low_stock_drinks = Drink.query.filter(Drink.quantity < reorder_threshold).all()
    
    # Export to CSV
    if request.method == 'POST' and 'export_csv' in request.form:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Drink Name', 'Current Stock'])
        for drink in low_stock_drinks:
            writer.writerow([drink.id, drink.name, drink.quantity])
        output.seek(0)
        return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=low_stock_report.csv"})
    
    # Export to PDF
    if request.method == 'POST' and 'export_pdf' in request.form:
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=letter)
        c.drawString(100, 750, "Low Stock Report")
        y = 700
        c.drawString(50, y, "ID")
        c.drawString(150, y, "Drink Name")
        c.drawString(300, y, "Current Stock")
        y -= 20
        for drink in low_stock_drinks:
            c.drawString(50, y, str(drink.id))
            c.drawString(150, y, drink.name)
            c.drawString(300, y, str(drink.quantity))
            y -= 20
        c.save()
        output.seek(0)
        return Response(output, mimetype='application/pdf', headers={"Content-Disposition": "attachment;filename=low_stock_report.pdf"})
    
    return render_template('low_stock_report.html', title="Low Stock Report", low_stock_drinks=low_stock_drinks)

# Create a new transaction record without specifying the date explicitly
#transaction = Transaction(user_id=current_user.id)
#db.session.add(transaction)

# This is for profit and loss
from flask import request, render_template, redirect, url_for, flash
from datetime import datetime, timedelta

@main.route('/profit_loss_report', methods=['GET', 'POST'])
@login_required
def profit_loss_report():
    # Default values for filtering
    time_range = request.form.get('time_range', 'day')
    selected_drink_id = request.form.get('drink_id', 'all')

    # Calculate the date range based on the selected time range
    today = datetime.today()
    if time_range == 'day':
        start_date = today
    elif time_range == 'week':
        start_date = today - timedelta(days=7)
    elif time_range == 'month':
        start_date = today - timedelta(days=30)
    elif time_range == 'year':
        start_date = today - timedelta(days=365)
    else:
        flash('Invalid time range selected', 'danger')
        return redirect(url_for('main.profit_loss_report'))

    # Query sales within the date range
    query = Sale.query.join(Drink).filter(Sale.date >= start_date)
    
    # Filter by selected drink if applicable
    if selected_drink_id != 'all':
        query = query.filter(Sale.drink_id == int(selected_drink_id))

    # Fetch the sales data
    sales = query.all()

    # Calculate total revenue, total cost, and profit
    total_revenue = sum(sale.total_price for sale in sales)
    total_cost = sum(sale.quantity * sale.drink.cost_price for sale in sales if sale.drink)
    total_profit = total_revenue - total_cost

    # Fetch all drinks for the dropdown selection
    drinks = Drink.query.all()

    return render_template(
        'profit_loss_report.html',
        title="Profit and Loss Report",
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_profit=total_profit,
        sales=sales,
        drinks=drinks,
        time_range=time_range,
        selected_drink_id=selected_drink_id
    )

#### Change password ###3

@main.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if current password is correct
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('main.change_password'))

        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('main.change_password'))

        # Update the password
        current_user.set_password(new_password)
        db.session.commit()

        flash('Password successfully changed!', 'success')
        return redirect(url_for('main.admin' if current_user.role == 'admin' else 'main.bartender'))

    return render_template('change_password.html', title="Change Password")

#### Change password ###


