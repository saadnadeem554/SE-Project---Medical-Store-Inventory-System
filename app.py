from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date, timedelta, time  # Added time here
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from io import StringIO
import csv
from sqlalchemy import func
import random
import time as time_module  # Rename the time module to avoid conflicts

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_store.db'
app.config['SECRET_KEY'] = 'your-secret-key-here'
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Add the user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'pharmacist', 'store_manager', or 'cashier'
    email = db.Column(db.String(120), nullable=True)  # Making email nullable for backward compatibility

    # Add property to make templates work
    @property
    def role(self):
        return self.user_type

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    min_stock_level = db.Column(db.Integer, default=10)
    expiry_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_expired(self):
        return self.expiry_date < datetime.now().date()
    
    def stock_status(self):
        if self.quantity <= 0:
            return "out_of_stock"
        elif self.quantity < self.min_stock_level:
            return "low_stock"
        else:
            return "well_stocked"

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    medicine = db.relationship('Medicine', backref=db.backref('sales', lazy=True))
    quantity = db.Column(db.Integer, nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=True)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def total_price(self):
        return self.quantity * self.sale_price

# Add this list near the top of your file, after imports
MEDICINE_CATEGORIES = [
    'Antibiotics',
    'Pain Relief',
    'Blood Thinners',
    'Cardiovascular',
    'Antidiabetic',
    'Antihistamines',
    'Antidepressants',
    'Antacids',
    'Antiviral',
    'Dermatological',
    'Eye/Ear Medications',
    'Hormonal',
    'Nutritional Supplements',
    'Respiratory',
    'Sedatives',
    'Vaccines',
    'Vitamins',
    'Other'
]

# Create database directory if it doesn't exist
if not os.path.exists('instance'):
    os.makedirs('instance')

# Check if database already exists
db_path = 'instance/medical_store.db'
db_exists = os.path.exists(db_path)

# Create all database tables
with app.app_context():
    db.create_all()

    # Only add default users if database is new
    if not db_exists or User.query.count() == 0 or Medicine.query.count() == 0:
        print("Creating new database with default users.")
        # Create default users
        pharmacist = User(
            username='pharmacist',
            password=generate_password_hash('pharmacist123'),
            user_type='pharmacist',
            email='pharmacist@example.com'
        )
        db.session.add(pharmacist)
        
        manager = User(
            username='manager',
            password=generate_password_hash('manager123'),
            user_type='store_manager',
            email='manager@example.com'
        )
        db.session.add(manager)
        
        cashier = User(
            username='cashier',
            password=generate_password_hash('cashier123'),
            user_type='cashier',
            email='cashier@example.com'
        )
        db.session.add(cashier)
        
        try:
            db.session.commit()
            print("Database initialized with default users.")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")
        
        # Add comprehensive sample medicines if none exist
        if Medicine.query.count() == 0:
            print("Adding sample medicines...")
            
            # Generate a variety of medicines across categories with different stock levels
            medicines = [
                # Antibiotics
                Medicine(
                    name='Amoxicillin 500mg', category='Antibiotics',
                    price=12.50, quantity=50, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1)
                ),
                Medicine(
                    name='Azithromycin 250mg', category='Antibiotics',
                    price=15.99, quantity=30, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2)
                ),
                Medicine(
                    name='Ciprofloxacin 500mg', category='Antibiotics',
                    price=18.75, quantity=25, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=6)
                ),
                Medicine(
                    name='Doxycycline 100mg', category='Antibiotics',
                    price=9.99, quantity=5, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=3)
                ),
                Medicine(
                    name='Metronidazole 400mg', category='Antibiotics',
                    price=7.25, quantity=0, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=9)
                ),
                
                # Pain Relief
                Medicine(
                    name='Paracetamol 500mg', category='Pain Relief',
                    price=5.99, quantity=120, min_stock_level=30,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 3)
                ),
                Medicine(
                    name='Ibuprofen 400mg', category='Pain Relief',
                    price=7.25, quantity=8, min_stock_level=25,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2)
                ),
                Medicine(
                    name='Aspirin 325mg', category='Pain Relief',
                    price=4.50, quantity=90, min_stock_level=20,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=6)
                ),
                Medicine(
                    name='Naproxen 500mg', category='Pain Relief',
                    price=8.75, quantity=45, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=8)
                ),
                Medicine(
                    name='Diclofenac Gel 1%', category='Pain Relief',
                    price=11.25, quantity=18, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=4)
                ),
                
                # Cardiovascular
                Medicine(
                    name='Lisinopril 10mg', category='Cardiovascular',
                    price=14.50, quantity=60, min_stock_level=20,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=3)
                ),
                Medicine(
                    name='Atorvastatin 20mg', category='Cardiovascular',
                    price=22.99, quantity=40, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=11)
                ),
                Medicine(
                    name='Amlodipine 5mg', category='Cardiovascular',
                    price=12.75, quantity=3, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=7)
                ),
                Medicine(
                    name='Warfarin 5mg', category='Cardiovascular',
                    price=8.50, quantity=0, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=10)
                ),
                Medicine(
                    name='Metoprolol 50mg', category='Cardiovascular',
                    price=10.25, quantity=35, min_stock_level=20,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=5)
                ),
                
                # Antidiabetic
                Medicine(
                    name='Metformin 500mg', category='Antidiabetic',
                    price=9.25, quantity=70, min_stock_level=25,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=8)
                ),
                Medicine(
                    name='Glipizide 5mg', category='Antidiabetic',
                    price=13.50, quantity=7, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=5)
                ),
                Medicine(
                    name='Insulin NPH 100IU', category='Antidiabetic',
                    price=42.99, quantity=22, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=2)
                ),
                Medicine(
                    name='Sitagliptin 100mg', category='Antidiabetic',
                    price=35.75, quantity=0, min_stock_level=8,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=4)
                ),
                
                # Antihistamines
                Medicine(
                    name='Cetirizine 10mg', category='Antihistamines',
                    price=8.99, quantity=85, min_stock_level=20,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=9)
                ),
                Medicine(
                    name='Loratadine 10mg', category='Antihistamines',
                    price=7.50, quantity=65, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=7)
                ),
                Medicine(
                    name='Diphenhydramine 25mg', category='Antihistamines',
                    price=6.25, quantity=4, min_stock_level=20,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=10)
                ),
                
                # Respiratory
                Medicine(
                    name='Salbutamol Inhaler', category='Respiratory',
                    price=18.99, quantity=28, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=9)
                ),
                Medicine(
                    name='Fluticasone Nasal Spray', category='Respiratory',
                    price=21.50, quantity=12, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=3)
                ),
                Medicine(
                    name='Montelukast 10mg', category='Respiratory',
                    price=19.75, quantity=0, min_stock_level=12,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=5)
                ),
                Medicine(
                    name='Budesonide Inhaler', category='Respiratory',
                    price=29.99, quantity=18, min_stock_level=8,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=8)
                ),
                
                # Vitamins
                Medicine(
                    name='Vitamin D3 2000IU', category='Vitamins',
                    price=12.99, quantity=95, min_stock_level=25,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 3, month=1)
                ),
                Medicine(
                    name='Vitamin B Complex', category='Vitamins',
                    price=15.50, quantity=78, min_stock_level=20,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=11)
                ),
                Medicine(
                    name='Vitamin C 1000mg', category='Vitamins',
                    price=9.99, quantity=110, min_stock_level=30,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=6)
                ),
                Medicine(
                    name='Multivitamin Daily', category='Vitamins',
                    price=18.25, quantity=6, min_stock_level=15,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=8)
                ),
                Medicine(
                    name='Vitamin E 400IU', category='Vitamins',
                    price=14.50, quantity=42, min_stock_level=12,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 3, month=3)
                ),
                
                # Dermatological
                Medicine(
                    name='Hydrocortisone Cream 1%', category='Dermatological',
                    price=11.99, quantity=25, min_stock_level=10,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=10)
                ),
                Medicine(
                    name='Clotrimazole Cream 1%', category='Dermatological',
                    price=9.25, quantity=9, min_stock_level=12,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 1, month=6)
                ),
                Medicine(
                    name='Benzoyl Peroxide Gel 2.5%', category='Dermatological',
                    price=12.75, quantity=0, min_stock_level=8,
                    expiry_date=datetime.now().date().replace(year=datetime.now().year + 2, month=2)
                ),
                
                # Some soon-to-expire medicines
                Medicine(
                    name='Expiring Soon Antibiotic', category='Antibiotics',
                    price=13.99, quantity=8, min_stock_level=10,
                    expiry_date=datetime.now().date() + timedelta(days=15)
                ),
                Medicine(
                    name='Expiring This Week', category='Pain Relief',
                    price=5.49, quantity=12, min_stock_level=10,
                    expiry_date=datetime.now().date() + timedelta(days=5)
                ),
                
                # Already expired medicines
                Medicine(
                    name='Expired Medication', category='Other',
                    price=9.99, quantity=3, min_stock_level=5,
                    expiry_date=datetime.now().date() - timedelta(days=30)
                )
            ]
            
            db.session.bulk_save_objects(medicines)
            try:
                db.session.commit()
                print("Sample medicines added to database.")
            except Exception as e:
                db.session.rollback()
                print(f"Error adding sample medicines: {e}")
                
            # Now generate sales data spanning multiple months
            print("Adding sample sales data...")
            
            # Get all medicines
            all_medicines = Medicine.query.all()
            if all_medicines:
                sales = []
                
                # Generate sales spanning the last 6 months
                end_date = datetime.now()
                start_date = end_date - timedelta(days=180)
                current_date = start_date
                
                # Customer name options
                customer_names = [
                    "John Smith", "Jane Doe", "Michael Johnson", "Emily Williams", 
                    "David Brown", "Sarah Miller", "Robert Jones", "Jennifer Davis",
                    "William Garcia", "Lisa Rodriguez", "Mark Wilson", "Patricia Martinez",
                    "Thomas Anderson", "Nancy Thompson", "Walk-in Customer", None  # Include some None/Walk-ins
                ]
                
                # Create random sales across the date range
                while current_date <= end_date:
                    # Generate between 0-8 sales per day with higher volume on weekdays
                    if current_date.weekday() < 5:  # Weekday (0-4)
                        num_sales = random.randint(3, 8)
                    else:  # Weekend (5-6)
                        num_sales = random.randint(0, 5)
                    
                    for _ in range(num_sales):
                        # Choose random medicine and quantity
                        medicine = random.choice(all_medicines)
                        
                        # Make popular medicines sell more
                        is_popular = medicine.category in ['Pain Relief', 'Antibiotics', 'Vitamins']
                        
                        if is_popular:
                            max_qty = 5
                        else:
                            max_qty = 3
                            
                        quantity = random.randint(1, max_qty)
                        
                        # Create sale with slight price variation sometimes
                        price_variation = random.uniform(0.95, 1.05)
                        sale_price = medicine.price * price_variation
                        
                        # Random time during business hours (8 AM - 8 PM)
                        hour = random.randint(8, 20)
                        minute = random.randint(0, 59)
                        second = random.randint(0, 59)
                        sale_datetime = datetime.combine(
                            current_date.date(), 
                            time(hour, minute, second)  # This now uses datetime.time
                        )
                        
                        # Random customer name or None
                        customer = random.choice(customer_names)
                        
                        sale = Sale(
                            medicine_id=medicine.id,
                            quantity=quantity,
                            sale_price=round(sale_price, 2),
                            customer_name=customer,
                            sale_date=sale_datetime
                        )
                        
                        sales.append(sale)
                    
                    # Move to next day
                    current_date += timedelta(days=1)
                
                # Add special sales patterns
                # 1. Holiday/promotion spike
                holiday_date = end_date - timedelta(days=random.randint(15, 45))
                for _ in range(25):  # Extra sales during promotion
                    medicine = random.choice(all_medicines)
                    quantity = random.randint(1, 5)
                    hour = random.randint(8, 20)
                    minute = random.randint(0, 59)
                    holiday_datetime = datetime.combine(
                        holiday_date.date(), 
                        time(hour, minute, random.randint(0, 59))
                    )
                    sale = Sale(
                        medicine_id=medicine.id,
                        quantity=quantity,
                        sale_price=round(medicine.price * 0.9, 2),  # 10% discount
                        customer_name=random.choice(customer_names),
                        sale_date=holiday_datetime
                    )
                    sales.append(sale)
                
                db.session.bulk_save_objects(sales)
                try:
                    db.session.commit()
                    print(f"Added {len(sales)} sample sales spanning multiple months.")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error adding sample sales: {e}")

    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Use Flask-Login's login_user function
            login_user(user)
            
            # Still set session variables if your code needs them elsewhere
            session['user_type'] = user.user_type
            session['username'] = user.username
            session['user_id'] = user.id
            
            # Check for low stock and notify store managers on login
            if user.role == 'store_manager':
                check_stock_and_notify()
                
                # Count low stock items to flash an alert
                low_stock_count = Medicine.query.filter(
                    Medicine.quantity > 0,
                    Medicine.quantity < Medicine.min_stock_level
                ).count()
                
                out_of_stock_count = Medicine.query.filter(
                    Medicine.quantity <= 0
                ).count()
                
                if low_stock_count > 0 or out_of_stock_count > 0:
                    flash(f'Alert: {low_stock_count} medicines with low stock and {out_of_stock_count} out of stock! Check Stock Levels for details.', 'warning')
            
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

# Replace the logout route
@app.route('/logout')
def logout():
    logout_user()  # Call Flask-Login's logout function
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Add this code at the top of your file after initialization
@app.route('/')
def root():
    # Redirect to login if not authenticated
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    # Check for low stock and notify store managers on EVERY visit if they're a manager
    if current_user.role == 'store_manager':
        check_stock_and_notify()
        
        # Count low stock items to flash an alert
        low_stock_count = Medicine.query.filter(
            Medicine.quantity > 0,
            Medicine.quantity < Medicine.min_stock_level
        ).count()
        
        out_of_stock_count = Medicine.query.filter(
            Medicine.quantity <= 0
        ).count()
        
        if low_stock_count > 0 or out_of_stock_count > 0:
            flash(f'Alert: {low_stock_count} medicines with low stock and {out_of_stock_count} out of stock! Check Stock Levels for details.', 'warning')
    
    return redirect(url_for('index'))

@app.route('/index')
@app.route('/inventory')
@login_required
def index():
    medicines = Medicine.query.all()
    now = datetime.now().date()
    
    # Calculate counts for the inventory overview chart
    well_stocked_count = 0
    low_stock_count = 0
    out_of_stock_count = 0
    
    for medicine in medicines:
        if medicine.quantity <= 0:
            out_of_stock_count += 1
        elif medicine.quantity < medicine.min_stock_level:
            low_stock_count += 1
        else:
            well_stocked_count += 1
    
    # Calculate total inventory value
    total_inventory_value = sum(medicine.quantity * medicine.price for medicine in medicines)
    
    return render_template('index.html', 
                          medicines=medicines, 
                          now=now,
                          well_stocked_count=well_stocked_count,
                          low_stock_count=low_stock_count,
                          out_of_stock_count=out_of_stock_count,
                          total_inventory_value=total_inventory_value)

# Add medicine route
@app.route('/add_medicine', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if current_user.role != 'pharmacist':
        flash('Only pharmacists can add medicines.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Get form data with proper validation
            name = request.form.get('name', '').strip()
            category = request.form.get('category', '').strip()
            price_str = request.form.get('price', '0')
            quantity_str = request.form.get('quantity', '0')
            min_stock_str = request.form.get('min_stock_level', '0')
            expiry_date_str = request.form.get('expiry_date', '')
            
            # Validate required fields
            if not name or not category:
                flash('Medicine name and category are required', 'error')
                return render_template('add_medicine.html', categories=MEDICINE_CATEGORIES)
            
            # Convert numeric values with proper error handling
            try:
                price = float(price_str)
                quantity = int(quantity_str)
                min_stock_level = int(min_stock_str)
            except ValueError:
                flash('Price, quantity and minimum stock must be valid numbers', 'error')
                return render_template('add_medicine.html', categories=MEDICINE_CATEGORIES)
                
            # Parse date with proper error handling
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD', 'error')
                return render_template('add_medicine.html', categories=MEDICINE_CATEGORIES)
            
            # Check for exact duplicates (same name, category, and expiry date)
            existing_medicine = Medicine.query.filter_by(
                name=name, 
                category=category,
                expiry_date=expiry_date
            ).first()
            
            if existing_medicine:
                flash(f'This exact medicine already exists with the same name, category, and expiry date.', 'error')
                return render_template('add_medicine.html', categories=MEDICINE_CATEGORIES)
                
            # Create medicine object
            medicine = Medicine(
                name=name,
                category=category,
                price=price,
                quantity=quantity,
                min_stock_level=min_stock_level,
                expiry_date=expiry_date
            )
            
            db.session.add(medicine)
            db.session.commit()
            
            flash('Medicine added successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding medicine: {str(e)}', 'error')
            return render_template('add_medicine.html', categories=MEDICINE_CATEGORIES)
    
    return render_template('add_medicine.html', categories=MEDICINE_CATEGORIES)

# Update medicine route
@app.route('/update_medicine/<int:id>', methods=['GET', 'POST'])
@login_required
def update_medicine(id):
    if current_user.role != 'pharmacist':
        flash('Access denied: Pharmacists only', 'error')
        return redirect(url_for('index'))
        
    medicine = Medicine.query.get_or_404(id)
    if request.method == 'POST':
        medicine.name = request.form['name']
        medicine.category = request.form['category']  # Changed from description to category
        medicine.quantity = int(request.form['quantity'])
        medicine.price = float(request.form['price'])
        medicine.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Medicine updated successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('update_medicine.html', medicine=medicine)

# Fix route name to match navigation link
@app.route('/remove_expired')
@login_required
def remove_expired():
    # Renamed from delete_expired to match navigation
    if current_user.role != 'store_manager':  # Use current_user for consistency
        flash('Only store managers can delete expired medicines.', 'error')
        return redirect(url_for('index'))

    try:
        expired_medicines = Medicine.query.filter(Medicine.expiry_date < datetime.now().date()).all()
        count = len(expired_medicines)
        
        for medicine in expired_medicines:
            db.session.delete(medicine)
        
        db.session.commit()
        flash(f'{count} expired medicines removed successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash('An error occurred while removing expired medicines.', 'error')

    return redirect(url_for('index'))

# Monitor stock levels
@app.route('/stock_levels')
@login_required
def stock_levels():
    if current_user.role not in ['store_manager', 'pharmacist']:
        flash('You do not have permission to view stock levels.', 'error')
        return redirect(url_for('index'))
    
    # Get the current date for expiry comparison
    now = datetime.now().date()
    
    # Define all the medicine categories
    out_of_stock = Medicine.query.filter(Medicine.quantity <= 0).all()
    low_stock = Medicine.query.filter(Medicine.quantity > 0, 
                                    Medicine.quantity < Medicine.min_stock_level).all()
    well_stocked = Medicine.query.filter(Medicine.quantity >= Medicine.min_stock_level).all()
    
    # Add this line to define the expired medicines
    expired = Medicine.query.filter(Medicine.expiry_date < now).all()
    
    # Add this line to get medicines expiring soon (within 30 days)
    expiring_soon = Medicine.query.filter(
        Medicine.expiry_date >= now,
        Medicine.expiry_date <= now + timedelta(days=30)
    ).all()
    
    # Create simple data structure of expiring medicines for JS
    expiring_data = {
        'this_week': 0,
        'this_month': 0,
        'expired': len(expired)
    }
    
    # Count medicines expiring this week and this month
    one_week_from_now = now + timedelta(days=7)
    one_month_from_now = now + timedelta(days=30)
    
    for medicine in expiring_soon:
        if medicine.expiry_date <= one_week_from_now:
            expiring_data['this_week'] += 1
        elif medicine.expiry_date <= one_month_from_now:
            expiring_data['this_month'] += 1
    
    return render_template('stock_levels.html', 
                          well_stocked=well_stocked, 
                          low_stock=low_stock, 
                          out_of_stock=out_of_stock,
                          expired=expired,
                          expiring_soon=expiring_soon,
                          expiring_data=expiring_data,
                          now=now)

# Fix route for sale creation - change session to current_user
@app.route('/sale', methods=['GET', 'POST'])
@login_required
def create_sale():
    if current_user.role not in ['cashier', 'pharmacist']:  # Changed from session to current_user
        flash('You do not have permission to make sales.', 'error')
        return redirect(url_for('index'))
    
    medicines = Medicine.query.all()
    
    if request.method == 'POST':
        medicine_id = request.form.get('medicine_id')
        quantity = int(request.form.get('quantity', 0))
        customer_name = request.form.get('customer_name', '')
        
        medicine = Medicine.query.get(medicine_id)
        if not medicine:
            flash('Medicine not found', 'error')
            return render_template('create_sale.html', medicines=medicines)
        
        # Check stock before sale
        if medicine.is_expired():
            flash("This medicine is expired and cannot be sold", 'error')
            return render_template('create_sale.html', medicines=medicines)
            
        if medicine.quantity < quantity:
            flash(f"Insufficient stock. Available: {medicine.quantity} units", 'error')
            return render_template('create_sale.html', medicines=medicines)
        
        sale = Sale(
            medicine_id=medicine_id,
            quantity=quantity,
            sale_price=medicine.price,
            customer_name=customer_name
        )
        
        medicine.quantity -= quantity
        
        try:
            db.session.add(sale)
            db.session.commit()
            flash('Sale completed successfully', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('Error processing sale', 'error')
    
    return render_template('create_sale.html', medicines=medicines)

# Reports dashboard
@app.route('/reports')
@login_required
def reports_dashboard():
    if current_user.role != 'store_manager':
        flash('Only store managers can access reports.', 'error')
        return redirect(url_for('index'))

    return render_template('reports_dashboard.html')

# Inventory status report
@app.route('/reports/inventory_status')
@login_required
def inventory_status_report():
    if current_user.role != 'store_manager':
        flash('Only store managers can access reports.', 'error')
        return redirect(url_for('index'))
    
    total_count = Medicine.query.count()
    expired_count = Medicine.query.filter(Medicine.expiry_date < datetime.now().date()).count()
    out_of_stock = Medicine.query.filter(Medicine.quantity <= 0).count()
    low_stock = Medicine.query.filter(Medicine.quantity > 0, 
                                    Medicine.quantity < Medicine.min_stock_level).count()
    well_stocked = Medicine.query.filter(Medicine.quantity >= Medicine.min_stock_level).count()
    
    categories = db.session.query(
        Medicine.category, func.count(Medicine.id)
    ).group_by(Medicine.category).all()
    
    # Pass the current timestamp directly to avoid using datetime in the template
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Add data for charts
    # Stock level pie chart
    stock_status_labels = ['Out of Stock', 'Low Stock', 'Well Stocked']
    stock_status_data = [out_of_stock, low_stock, well_stocked]
    
    # Category distribution
    category_data = db.session.query(
        Medicine.category, func.count(Medicine.id)
    ).group_by(Medicine.category).all()
    
    category_labels = [item[0] for item in category_data]
    category_values = [item[1] for item in category_data]
    
    # Value by category
    value_by_category = db.session.query(
        Medicine.category, func.sum(Medicine.price * Medicine.quantity)
    ).group_by(Medicine.category).all()
    
    value_category_labels = [item[0] for item in value_by_category]
    value_category_data = [float(item[1]) for item in value_by_category]
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template(
        'inventory_status_report.html',
        # Existing parameters...
        total_count=total_count,
        expired_count=expired_count,
        out_of_stock=out_of_stock,
        low_stock=low_stock,
        well_stocked=well_stocked,
        categories=categories,
        current_time=current_time,
        # New chart data
        stock_status_labels=stock_status_labels,
        stock_status_data=stock_status_data,
        category_labels=category_labels,
        category_values=category_values,
        value_category_labels=value_category_labels,
        value_category_data=value_category_data
    )

# Export inventory as CSV
@app.route('/reports/export_inventory_csv')
@login_required
def export_inventory_csv():
    if current_user.role != 'store_manager':  # Changed from session to current_user
        flash('Only store managers can access reports.', 'error')
        return redirect(url_for('index'))
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Category', 'Price', 'Quantity', 
                    'Minimum Stock', 'Expiry Date', 'Stock Status', 'Created At', 'Updated At'])
    
    medicines = Medicine.query.all()
    
    for medicine in medicines:
        writer.writerow([
            medicine.id,
            medicine.name,
            medicine.category,
            medicine.price,
            medicine.quantity,
            medicine.min_stock_level,
            medicine.expiry_date.strftime('%Y-%m-%d'),
            medicine.stock_status(),
            medicine.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            medicine.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=inventory_report.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

def check_stock_and_notify():
    """Helper function to check stock levels"""
    with app.app_context():
        low_stock_items = Medicine.query.filter(
            Medicine.quantity > 0,
            Medicine.quantity < Medicine.min_stock_level
        ).all()
        
        out_of_stock_items = Medicine.query.filter(Medicine.quantity <= 0).all()
        
        # We don't need to add notifications to database anymore
        # Just return the counts for flashing messages if needed
        return len(low_stock_items), len(out_of_stock_items)

# Route to manually trigger stock check
@app.route('/check_stock')
@login_required
def check_stock():
    # Change session check to current_user
    if current_user.role != 'store_manager':
        flash('Only store managers can perform stock checks.', 'error')
        return redirect(url_for('index'))
    
    check_stock_and_notify()
    flash('Stock check completed. Check notifications for any alerts.', 'success')
    return redirect(url_for('stock_levels'))

# Use Flask's before_request to check stock levels automatically
# This is more efficient than checking on every request
last_check = datetime.now()

@app.before_request
def auto_check_stock():
    global last_check
    # Only check once per hour to avoid overloading the system
    if (datetime.now() - last_check).total_seconds() > 3600:  # 3600 seconds = 1 hour
        # Only check on certain routes to avoid checking too frequently
        if request.endpoint in ['index', 'stock_levels', 'inventory_status_report']:
            check_stock_and_notify()
            last_check = datetime.now()

@app.route('/reports/export_sales_csv')
@login_required
def export_sales_csv():
    if current_user.role != 'store_manager':
        flash('Only store managers can export sales data.', 'error')
        return redirect(url_for('index'))
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Sale ID', 'Date', 'Medicine', 'Category', 'Quantity', 
                     'Unit Price', 'Total', 'Customer'])
    
    sales = Sale.query.join(Medicine).order_by(Sale.sale_date.desc()).all()
    
    for sale in sales:
        writer.writerow([
            sale.id,
            sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            sale.medicine.name,
            sale.medicine.category,
            sale.quantity,
            f"${sale.sale_price:.2f}",
            f"${sale.total_price:.2f}",
            sale.customer_name or 'Walk-in Customer'
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=sales_report.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

@app.route('/sales_report')
@login_required
def sales_report():
    if current_user.role != 'store_manager':
        flash('Access denied. Store managers only.', 'error')
        return redirect(url_for('index'))
    
    # Get all sales for basic statistics
    sales = Sale.query.all()
    total_revenue = sum(sale.total_price for sale in sales) if sales else 0
    total_sales_count = len(sales)
    
    # Current time for report header
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Daily sales for the past 7 days
    end_date = datetime.now().date()
    
    daily_sales = []
    daily_labels = []
    
    for i in range(7):
        day = end_date - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        day_sales = db.session.query(func.sum(Sale.quantity * Sale.sale_price)).filter(
            Sale.sale_date >= day_start,
            Sale.sale_date <= day_end
        ).scalar() or 0
        
        daily_sales.insert(0, float(day_sales))
        daily_labels.insert(0, day.strftime('%Y-%m-%d'))
    
    # Monthly revenue data
    monthly_data = {}
    for sale in sales:
        month_key = sale.sale_date.strftime('%Y-%m')
        if month_key in monthly_data:
            monthly_data[month_key] += sale.total_price
        else:
            monthly_data[month_key] = sale.total_price
    
    # Sort by month
    sorted_months = sorted(monthly_data.keys()) if monthly_data else []
    month_labels = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months]
    month_values = [monthly_data[m] for m in sorted_months]
    
    # Sales by category
    category_data = db.session.query(
        Medicine.category, func.sum(Sale.quantity * Sale.sale_price)
    ).join(Medicine, Medicine.id == Sale.medicine_id).group_by(
        Medicine.category
    ).all()
    
    category_labels = [item[0] for item in category_data]
    category_values = [float(item[1]) for item in category_data]
    
    # Top selling products
    product_sales = {}
    for sale in sales:
        medicine = Medicine.query.get(sale.medicine_id)
        if medicine:
            if medicine.name in product_sales:
                product_sales[medicine.name] += sale.quantity
            else:
                product_sales[medicine.name] = sale.quantity
    
    # Sort products by sales quantity and get top 5
    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5] if product_sales else []
    product_labels = [p[0] for p in top_products]
    product_values = [p[1] for p in top_products]
    
    return render_template('sales_report.html', 
                          sales=sales, 
                          total_revenue=total_revenue,
                          total_sales_count=total_sales_count,
                          daily_labels=daily_labels,
                          daily_sales=daily_sales,
                          month_labels=month_labels,
                          month_values=month_values,
                          category_labels=category_labels,
                          category_values=category_values,
                          product_labels=product_labels,
                          product_values=product_values,
                          current_time=current_time)

# Fix the context processor to ensure notifications are always updated
@app.context_processor
def inject_medicines():
    if current_user.is_authenticated:
        # Always check stock for store managers
        if current_user.role == 'store_manager':
            check_stock_and_notify()
        
        medicines = Medicine.query.all()
        
        # Calculate notification counts directly in the context processor
        low_stock_count = 0
        out_of_stock_count = 0
        
        for medicine in medicines:
            if medicine.quantity <= 0:
                out_of_stock_count += 1
            elif medicine.quantity < medicine.min_stock_level:
                low_stock_count += 1
                
        return {
            'medicines': medicines,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'notification_count': low_stock_count + out_of_stock_count
        }
    return {'medicines': [], 'low_stock_count': 0, 'out_of_stock_count': 0, 'notification_count': 0}

@app.route('/delete_medicine', methods=['GET', 'POST'])
@login_required
def delete_medicine():
    if current_user.role != 'pharmacist':
        flash('Access denied: Pharmacists only', 'error')
        return redirect(url_for('index'))
    
    medicines = Medicine.query.all()
    
    if request.method == 'POST':
        medicine_id = request.form.get('medicine_id')
        
        if not medicine_id:
            flash('Please select a medicine', 'error')
            return redirect(url_for('delete_medicine'))
        
        try:
            medicine = Medicine.query.get_or_404(medicine_id)
            medicine_name = medicine.name
            
            # Check if there are sales records for this medicine
            sales_count = Sale.query.filter_by(medicine_id=medicine_id).count()
            if sales_count > 0:
                flash(f'Cannot delete {medicine_name} because it has {sales_count} sales records', 'error')
                return redirect(url_for('delete_medicine'))
            
            db.session.delete(medicine)
            db.session.commit()
            flash(f'Medicine {medicine_name} deleted successfully', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting medicine: {str(e)}', 'error')
    
    return render_template('delete_medicine.html', medicines=medicines)

@app.route('/delete_medicine_direct/<int:id>', methods=['POST'])
@login_required
def delete_medicine_direct(id):
    if current_user.role != 'pharmacist':
        flash('Access denied: Pharmacists only', 'error')
        return redirect(url_for('index'))
    
    try:
        medicine = Medicine.query.get_or_404(id)
        medicine_name = medicine.name
        
        # Check if there are sales records for this medicine
        sales_count = Sale.query.filter_by(medicine_id=id).count()
        if sales_count > 0:
            flash(f'Cannot delete {medicine_name} because it has {sales_count} sales records', 'error')
            return redirect(url_for('index'))
        
        db.session.delete(medicine)
        db.session.commit()
        flash(f'Medicine {medicine_name} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting medicine: {str(e)}', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)