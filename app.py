from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_store.db'
app.config['SECRET_KEY'] = 'your-secret-key-here'
db = SQLAlchemy(app)

# Login decorator to ensure user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'pharmacist' or 'store_manager'

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_expired(self):
        return self.expiry_date < datetime.now().date()

# Create all database tables
with app.app_context():
    db.create_all()
    # Create default users if they don't exist
    if not User.query.filter_by(username='pharmacist').first():
        pharmacist = User(
            username='pharmacist',
            password=generate_password_hash('pharmacist123'),
            user_type='pharmacist'
        )
        db.session.add(pharmacist)
    
    if not User.query.filter_by(username='manager').first():
        manager = User(
            username='manager',
            password=generate_password_hash('manager123'),
            user_type='store_manager'
        )
        db.session.add(manager)
    
    try:
        db.session.commit()
    except:
        db.session.rollback()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_type'] = user.user_type
            session['username'] = user.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    medicines = Medicine.query.all()
    return render_template('index.html', medicines=medicines)

@app.route('/add_medicine', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if session['user_type'] != 'pharmacist':
        flash('Only pharmacists can add medicines.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Validate input fields
            name = request.form['name'].strip()
            category = request.form['category'].strip()
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()

            if not all([name, category]) or price <= 0 or quantity < 0:
                raise ValueError("Invalid input data")

            medicine = Medicine(
                name=name,
                category=category,
                price=price,
                quantity=quantity,
                expiry_date=expiry_date
            )
            
            db.session.add(medicine)
            db.session.commit()
            flash('Medicine added successfully!', 'success')
            return redirect(url_for('index'))

        except ValueError as e:
            flash('Please check your input data.', 'error')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding medicine.', 'error')

    return render_template('add_medicine.html')

@app.route('/update_medicine/<int:id>', methods=['GET', 'POST'])
@login_required
def update_medicine(id):
    if session['user_type'] != 'pharmacist':
        flash('Only pharmacists can update medicines.', 'error')
        return redirect(url_for('index'))

    medicine = Medicine.query.get_or_404(id)

    if request.method == 'POST':
        try:
            medicine.name = request.form['name'].strip()
            medicine.category = request.form['category'].strip()
            medicine.price = float(request.form['price'])
            medicine.quantity = int(request.form['quantity'])
            medicine.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-d').date()

            if not all([medicine.name, medicine.category]) or medicine.price <= 0 or medicine.quantity < 0:
                raise ValueError("Invalid input data")

            db.session.commit()
            flash('Medicine updated successfully!', 'success')
            return redirect(url_for('index'))

        except ValueError:
            flash('Please check your input data.', 'error')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating medicine.', 'error')

    return render_template('update_medicine.html', medicine=medicine)

@app.route('/delete_expired')
@login_required
def delete_expired():
    if session['user_type'] != 'store_manager':
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

if __name__ == '__main__':
    app.run(debug=True)