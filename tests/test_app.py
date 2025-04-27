import pytest
import sys
import os
import datetime
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, Mock
from flask import session, url_for

# Add the parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Medicine, User, Sale
from app import check_stock_and_notify, MEDICINE_CATEGORIES

@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create test users
            pharmacist = User(
                username='test_pharmacist',
                password='password',  # Not hashed for tests
                user_type='pharmacist',
                email='test@example.com'
            )
            manager = User(
                username='test_manager',
                password='password',
                user_type='store_manager',
                email='manager@example.com'
            )
            cashier = User(
                username='test_cashier',
                password='password',
                user_type='cashier',
                email='cashier@example.com'
            )
            db.session.add_all([pharmacist, manager, cashier])
            db.session.commit()
            
            yield client
            
            # Teardown
            db.session.remove()
            db.drop_all()

@pytest.fixture
def auth_pharmacist(client):
    """Helper to log in as pharmacist"""
    with client.session_transaction() as sess:
        sess['user_type'] = 'pharmacist'
        sess['username'] = 'test_pharmacist'
        sess['user_id'] = 1
        sess['_user_id'] = 1  # For Flask-Login
    return client

@pytest.fixture
def auth_manager(client):
    """Helper to log in as store manager"""
    with client.session_transaction() as sess:
        sess['user_type'] = 'store_manager'
        sess['username'] = 'test_manager'
        sess['user_id'] = 2
        sess['_user_id'] = 2  # For Flask-Login
    return client

@pytest.fixture
def auth_cashier(client):
    """Helper to log in as cashier"""
    with client.session_transaction() as sess:
        sess['user_type'] = 'cashier'
        sess['username'] = 'test_cashier'
        sess['user_id'] = 3
        sess['_user_id'] = 3  # For Flask-Login
    return client

@pytest.fixture
def sample_medicine():
    """Create a sample medicine for testing"""
    return {
        'name': 'Test Antibiotic',
        'category': 'Antibiotics',
        'price': 10.50,
        'quantity': 50,
        'min_stock_level': 10,
        'expiry_date': (datetime.datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    }

@pytest.fixture
def expired_medicine():
    """Create an expired medicine for testing"""
    return {
        'name': 'Expired Medicine',
        'category': 'Antibiotics',
        'price': 15.75,
        'quantity': 5,
        'min_stock_level': 10,
        'expiry_date': (datetime.datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    }

@pytest.fixture
def low_stock_medicine():
    """Create a low stock medicine for testing"""
    return {
        'name': 'Low Stock Medicine',
        'category': 'Pain Relief',
        'price': 5.99,
        'quantity': 5,
        'min_stock_level': 10,
        'expiry_date': (datetime.datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
    }


# ==== TEST LOGIN/AUTHENTICATION ====

def test_login_success(client):
    """Test successful login attempts."""
    with patch('app.check_password_hash', return_value=True):
        response = client.post('/login', data={
            'username': 'test_pharmacist',
            'password': 'password'
        }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Logged in successfully' in response.data

def test_login_failure(client):
    """Test failed login attempts."""
    with patch('app.check_password_hash', return_value=False):
        response = client.post('/login', data={
            'username': 'test_pharmacist',
            'password': 'wrong_password'
        }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data

def test_logout(auth_pharmacist):
    """Test user logout."""
    response = auth_pharmacist.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logged out successfully' in response.data

# ==== TEST MEDICINE MANAGEMENT (PHARMACIST) ====

def test_add_medicine_success(auth_pharmacist, sample_medicine):
    """Test adding a new medicine."""
    response = auth_pharmacist.post('/add_medicine', 
                               data=sample_medicine,
                               follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Medicine added successfully' in response.data
    
    # Verify medicine was added to database
    with app.app_context():
        medicine = Medicine.query.filter_by(name=sample_medicine['name']).first()
        assert medicine is not None
        assert medicine.name == sample_medicine['name']
        assert medicine.category == sample_medicine['category']
        assert medicine.price == sample_medicine['price']
        assert medicine.quantity == sample_medicine['quantity']

def test_add_medicine_duplicate(auth_pharmacist, sample_medicine):
    """Test adding a duplicate medicine."""
    # First add the medicine
    auth_pharmacist.post('/add_medicine', data=sample_medicine)
    
    # Try to add it again
    response = auth_pharmacist.post('/add_medicine', 
                               data=sample_medicine,
                               follow_redirects=True)
    
    assert b'already exists' in response.data

def test_add_medicine_validation(auth_pharmacist):
    """Test validation when adding medicine."""
    # Missing required fields
    response = auth_pharmacist.post('/add_medicine', 
                               data={'name': '', 'category': ''},
                               follow_redirects=True)
    
    assert b'Medicine name and category are required' in response.data
    
    # Invalid price
    response = auth_pharmacist.post('/add_medicine', 
                               data={
                                   'name': 'Test Med', 
                                   'category': 'Antibiotics',
                                   'price': 'not-a-price',
                                   'quantity': '10',
                                   'min_stock_level': '5',
                                   'expiry_date': '2023-12-31'
                               },
                               follow_redirects=True)
    
    assert b'Price, quantity and minimum stock must be valid numbers' in response.data
    
    # Invalid date format
    response = auth_pharmacist.post('/add_medicine', 
                               data={
                                   'name': 'Test Med', 
                                   'category': 'Antibiotics',
                                   'price': '10.99',
                                   'quantity': '10',
                                   'min_stock_level': '5',
                                   'expiry_date': 'not-a-date'
                               },
                               follow_redirects=True)
    
    assert b'Invalid date format' in response.data

def test_update_medicine(auth_pharmacist, sample_medicine):
    """Test updating medicine details."""
    # First add a medicine
    auth_pharmacist.post('/add_medicine', data=sample_medicine)
    
    # Get the medicine ID
    with app.app_context():
        medicine = Medicine.query.filter_by(name=sample_medicine['name']).first()
        medicine_id = medicine.id
    
    # Update the medicine - add the missing min_stock_level field
    updated_data = {
        'name': 'Updated Medicine',
        'category': 'Antibiotics',
        'price': '15.75',
        'quantity': '65',
        'min_stock_level': '15',  # Add the missing field
        'expiry_date': (datetime.datetime.now() + timedelta(days=500)).strftime('%Y-%m-%d')
    }
    
    response = auth_pharmacist.post(f'/update_medicine/{medicine_id}',
                               data=updated_data,
                               follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Medicine updated successfully' in response.data
    
    # Verify medicine was updated in database
    with app.app_context():
        updated = Medicine.query.get(medicine_id)
        assert updated.name == updated_data['name']
        assert updated.price == float(updated_data['price'])
        assert updated.quantity == int(updated_data['quantity'])
        assert updated.min_stock_level == int(updated_data['min_stock_level'])

def test_delete_medicine(auth_pharmacist, sample_medicine):
    """Test deleting a medicine."""
    # First add a medicine
    auth_pharmacist.post('/add_medicine', data=sample_medicine)
    
    # Get the medicine ID
    with app.app_context():
        medicine = Medicine.query.filter_by(name=sample_medicine['name']).first()
        medicine_id = medicine.id
    
    # Delete the medicine
    response = auth_pharmacist.post(f'/delete_medicine_direct/{medicine_id}',
                               follow_redirects=True)
    
    assert response.status_code == 200
    assert b'deleted successfully' in response.data
    
    # Verify medicine was deleted from database
    with app.app_context():
        deleted = Medicine.query.get(medicine_id)
        assert deleted is None

def test_non_pharmacist_cannot_add_medicine(auth_cashier, sample_medicine):
    """Test that non-pharmacists cannot add medicines."""
    response = auth_cashier.post('/add_medicine', 
                            data=sample_medicine,
                            follow_redirects=True)
    
    assert b'Only pharmacists can add medicines' in response.data

# ==== TEST EXPIRED MEDICINE HANDLING (STORE MANAGER) ====

def test_remove_expired_medicines(auth_manager, expired_medicine):
    """Test removing expired medicines."""
    # Add an expired medicine
    with app.app_context():
        expired = Medicine(
            name=expired_medicine['name'],
            category=expired_medicine['category'],
            price=expired_medicine['price'],
            quantity=expired_medicine['quantity'],
            min_stock_level=expired_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(expired_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(expired)
        db.session.commit()
    
    # Use the remove expired route
    response = auth_manager.get('/remove_expired', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'expired medicines removed successfully' in response.data
    
    # Verify expired medicine was removed from database
    with app.app_context():
        expired_count = Medicine.query.filter_by(name=expired_medicine['name']).count()
        assert expired_count == 0

def test_non_manager_cannot_remove_expired(auth_cashier, expired_medicine):
    """Test that non-managers cannot remove expired medicines."""
    # Add an expired medicine
    with app.app_context():
        expired = Medicine(
            name=expired_medicine['name'],
            category=expired_medicine['category'],
            price=expired_medicine['price'],
            quantity=expired_medicine['quantity'],
            min_stock_level=expired_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(expired_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(expired)
        db.session.commit()
    
    # Try to remove expired as cashier
    response = auth_cashier.get('/remove_expired', follow_redirects=True)
    
    assert b'Only store managers can delete expired medicines' in response.data
    
    # Verify expired medicine is still in database
    with app.app_context():
        expired_count = Medicine.query.filter_by(name=expired_medicine['name']).count()
        assert expired_count == 1

# ==== TEST STOCK MANAGEMENT ====

def test_stock_levels_access(auth_manager):
    """Test accessing stock levels as manager."""
    response = auth_manager.get('/stock_levels')
    
    assert response.status_code == 200
    assert b'Stock Levels' in response.data
    assert b'Out of Stock' in response.data
    assert b'Low Stock' in response.data
    assert b'Well Stocked' in response.data

def test_stock_levels_pharmacist_access(auth_pharmacist):
    """Test accessing stock levels as pharmacist."""
    response = auth_pharmacist.get('/stock_levels')
    
    assert response.status_code == 200
    # Pharmacists should also be able to view stock levels

def test_stock_levels_cashier_access(auth_cashier):
    """Test accessing stock levels as cashier (should be denied)."""
    response = auth_cashier.get('/stock_levels', follow_redirects=True)
    
    assert b'You do not have permission to view stock levels' in response.data

def test_check_stock_notification(auth_manager, low_stock_medicine):
    """Test low stock notifications."""
    # Add a low stock medicine
    with app.app_context():
        low_stock = Medicine(
            name=low_stock_medicine['name'],
            category=low_stock_medicine['category'],
            price=low_stock_medicine['price'],
            quantity=low_stock_medicine['quantity'],
            min_stock_level=low_stock_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(low_stock_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(low_stock)
        db.session.commit()
    
    # Manually trigger stock check
    response = auth_manager.get('/check_stock', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Stock check completed' in response.data
    
    # Now check for low stock in the stock levels page
    response = auth_manager.get('/stock_levels')
    assert low_stock_medicine['name'].encode() in response.data
    assert b'Low Stock' in response.data

# ==== TEST SALES TRANSACTIONS (CASHIER) ====

def test_create_sale_success(auth_cashier, sample_medicine):
    """Test creating a valid sale."""
    # Add medicine to inventory
    with app.app_context():
        medicine = Medicine(
            name=sample_medicine['name'],
            category=sample_medicine['category'],
            price=sample_medicine['price'],
            quantity=sample_medicine['quantity'],
            min_stock_level=sample_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(sample_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(medicine)
        db.session.commit()
        medicine_id = medicine.id
        initial_quantity = medicine.quantity
    
    # Create a sale
    sale_data = {
        'medicine_id': medicine_id,
        'quantity': 5,
        'customer_name': 'Test Customer'
    }
    
    response = auth_cashier.post('/sale', data=sale_data, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Sale completed successfully' in response.data
    
    # Verify inventory was updated
    with app.app_context():
        updated_medicine = Medicine.query.get(medicine_id)
        assert updated_medicine.quantity == initial_quantity - sale_data['quantity']
        
        # Verify sale record was created
        sale = Sale.query.filter_by(medicine_id=medicine_id).first()
        assert sale is not None
        assert sale.quantity == sale_data['quantity']
        assert sale.customer_name == sale_data['customer_name']
        assert sale.medicine_name == sample_medicine['name']
        assert sale.medicine_category == sample_medicine['category']

def test_create_sale_insufficient_stock(auth_cashier, sample_medicine):
    """Test trying to create a sale with insufficient stock."""
    # Add medicine with limited quantity
    with app.app_context():
        medicine = Medicine(
            name=sample_medicine['name'],
            category=sample_medicine['category'],
            price=sample_medicine['price'],
            quantity=10,  # Limited quantity
            min_stock_level=sample_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(sample_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(medicine)
        db.session.commit()
        medicine_id = medicine.id
    
    # Try to create a sale with quantity > available
    sale_data = {
        'medicine_id': medicine_id,
        'quantity': 15,  # More than available
        'customer_name': 'Test Customer'
    }
    
    response = auth_cashier.post('/sale', data=sale_data, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Insufficient stock' in response.data
    
    # Verify inventory was NOT updated
    with app.app_context():
        medicine = Medicine.query.get(medicine_id)
        assert medicine.quantity == 10  # Still the same

def test_create_sale_expired_medicine(auth_cashier, expired_medicine):
    """Test trying to sell an expired medicine."""
    # Add expired medicine
    with app.app_context():
        medicine = Medicine(
            name=expired_medicine['name'],
            category=expired_medicine['category'],
            price=expired_medicine['price'],
            quantity=expired_medicine['quantity'],
            min_stock_level=expired_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(expired_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(medicine)
        db.session.commit()
        medicine_id = medicine.id
    
    # Try to create a sale for expired medicine
    sale_data = {
        'medicine_id': medicine_id,
        'quantity': 1,
        'customer_name': 'Test Customer'
    }
    
    response = auth_cashier.post('/sale', data=sale_data, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'expired and cannot be sold' in response.data
    
    # Verify inventory was NOT updated
    with app.app_context():
        medicine = Medicine.query.get(medicine_id)
        assert medicine.quantity == expired_medicine['quantity']  # Still the same

def test_non_cashier_cannot_create_sale(auth_manager, sample_medicine):
    """Test that store managers cannot create sales."""
    # Add medicine to inventory
    with app.app_context():
        medicine = Medicine(
            name=sample_medicine['name'],
            category=sample_medicine['category'],
            price=sample_medicine['price'],
            quantity=sample_medicine['quantity'],
            min_stock_level=sample_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(sample_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(medicine)
        db.session.commit()
        medicine_id = medicine.id
    
    # Try to create a sale as manager
    sale_data = {
        'medicine_id': medicine_id,
        'quantity': 5,
        'customer_name': 'Test Customer'
    }
    
    response = auth_manager.post('/sale', data=sale_data, follow_redirects=True)
    
    assert b'You do not have permission to make sales' in response.data

# ==== TEST REPORTING (STORE MANAGER) ====

def test_reports_dashboard_access(auth_manager):
    """Test accessing reports dashboard as manager."""
    response = auth_manager.get('/reports')
    
    assert response.status_code == 200
    assert b'Reports Dashboard' in response.data

def test_inventory_status_report(auth_manager):
    """Test accessing inventory status report."""
    response = auth_manager.get('/reports/inventory_status')
    
    assert response.status_code == 200
    assert b'Inventory Status Report' in response.data

def test_export_inventory_csv(auth_manager, sample_medicine):
    """Test exporting inventory as CSV."""
    # Add a medicine for the report
    with app.app_context():
        medicine = Medicine(
            name=sample_medicine['name'],
            category=sample_medicine['category'],
            price=sample_medicine['price'],
            quantity=sample_medicine['quantity'],
            min_stock_level=sample_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(sample_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(medicine)
        db.session.commit()
    
    # Export inventory CSV
    response = auth_manager.get('/reports/export_inventory_csv')
    
    assert response.status_code == 200
    assert response.headers['Content-Disposition'] == 'attachment; filename=inventory_report.csv'
    assert sample_medicine['name'] in response.data.decode('utf-8')

def test_export_sales_csv(auth_manager, sample_medicine):
    """Test exporting sales as CSV."""
    # Add a medicine and a sale for the report
    with app.app_context():
        medicine = Medicine(
            name=sample_medicine['name'],
            category=sample_medicine['category'],
            price=sample_medicine['price'],
            quantity=sample_medicine['quantity'],
            min_stock_level=sample_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(sample_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(medicine)
        db.session.commit()
        
        sale = Sale(
            medicine_id=medicine.id,
            medicine_name=medicine.name,
            medicine_category=medicine.category,
            quantity=5,
            sale_price=medicine.price,
            customer_name='Test Customer',
            sale_date=datetime.datetime.now()
        )
        db.session.add(sale)
        db.session.commit()
    
    # Export sales CSV
    response = auth_manager.get('/reports/export_sales_csv')
    
    assert response.status_code == 200
    assert response.headers['Content-Disposition'] == 'attachment; filename=sales_report.csv'
    assert 'Test Customer' in response.data.decode('utf-8')

def test_sales_report(auth_manager, sample_medicine):
    """Test accessing sales report."""
    # Add a medicine and a sale for the report
    with app.app_context():
        medicine = Medicine(
            name=sample_medicine['name'],
            category=sample_medicine['category'],
            price=sample_medicine['price'],
            quantity=sample_medicine['quantity'],
            min_stock_level=sample_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(sample_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(medicine)
        db.session.commit()
        
        sale = Sale(
            medicine_id=medicine.id,
            medicine_name=medicine.name,
            medicine_category=medicine.category,
            quantity=5,
            sale_price=medicine.price,
            customer_name='Test Customer',
            sale_date=datetime.datetime.now()
        )
        db.session.add(sale)
        db.session.commit()
    
    # Access sales report
    response = auth_manager.get('/sales_report')
    
    assert response.status_code == 200
    assert b'Sales Report' in response.data

def test_non_manager_cannot_access_reports(auth_cashier):
    """Test that non-managers cannot access reports."""
    response = auth_cashier.get('/reports', follow_redirects=True)
    assert b'Only store managers can access reports' in response.data
    
    response = auth_cashier.get('/reports/inventory_status', follow_redirects=True)
    assert b'Only store managers can access reports' in response.data
    
    response = auth_cashier.get('/reports/export_inventory_csv', follow_redirects=True)
    assert b'Only store managers can access reports' in response.data
    
    response = auth_cashier.get('/sales_report', follow_redirects=True)
    assert b'Access denied. Store managers only' in response.data

# ==== TEST UTILITY FUNCTIONS ====

# ==== TEST UTILITY FUNCTIONS ====

def test_check_stock_and_notify(client, low_stock_medicine):
    """Test the check_stock_and_notify function."""
    # Use the client fixture to ensure database tables are created
    
    # Add a low stock medicine
    with app.app_context():
        # Create all tables to make sure they exist
        db.create_all()
        
        low_stock = Medicine(
            name=low_stock_medicine['name'],
            category=low_stock_medicine['category'],
            price=low_stock_medicine['price'],
            quantity=low_stock_medicine['quantity'],
            min_stock_level=low_stock_medicine['min_stock_level'],
            expiry_date=datetime.datetime.strptime(low_stock_medicine['expiry_date'], '%Y-%m-%d').date()
        )
        db.session.add(low_stock)
        db.session.commit()
        
        # Call the function
        low_count, out_count = check_stock_and_notify(in_context=True)
        
        # Verify it detected the low stock
        assert low_count >= 1