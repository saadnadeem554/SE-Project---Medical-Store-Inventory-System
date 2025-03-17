# Pharmacy Management System

## Overview

The Pharmacy Management System is a comprehensive web application designed to help pharmacists, store managers, and cashiers efficiently manage a medical store. It provides robust features for inventory tracking, sales management, and comprehensive reporting.

![Pharmacy Management System](https://img.shields.io/badge/Flask-Pharmacy%20Management-blue)

## Features

### User Authentication
- Role-based access control (Pharmacist, Store Manager, Cashier)
- Secure login/logout functionality
- Password hashing for enhanced security

### Inventory Management
- Add, update, and delete medicines
- Track stock levels with automatic alerts
- Monitor expiry dates
- Remove expired medications

### Sales Processing
- Create and record sales transactions
- Track sales by customer
- Price variation support
- Inventory updates upon sale

### Comprehensive Reporting
- Inventory status reports with stock levels
- Sales analysis with daily and monthly trends
- Category-based sales distribution
- Export data to CSV format

### Stock Monitoring
- Low stock notifications
- Out-of-stock alerts
- Expiry date warnings
- Stock level visualization

## Technology Stack

- **Backend**: Python, Flask
- **Database**: SQLAlchemy (SQLite)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Visualization**: Chart.js
- **Authentication**: Flask-Login

## Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pharmacy-management-system.git
   cd pharmacy-management-system
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   flask run
   ```
   The application will automatically create and populate the database with sample data on first run.

5. **Access the application**
   ```
   http://localhost:5000
   ```

## Default User Credentials

| Username   | Password      | Role          |
|------------|---------------|---------------|
| pharmacist | pharmacist123 | Pharmacist    |
| manager    | manager123    | Store Manager |
| cashier    | cashier123    | Cashier       |

## Role Permissions

### Pharmacist
- Add new medicines
- Update medicine details
- Delete medicines
- Make sales
- View inventory

### Store Manager
- View comprehensive reports
- Export data to CSV
- Remove expired medicines
- Monitor stock levels
- Receive alerts for low stock

### Cashier
- Make sales
- View inventory

## Screenshots

![image](https://github.com/user-attachments/assets/955a1627-c125-4a17-b077-08b82f6b2eac)
![image](https://github.com/user-attachments/assets/0f467de1-cc2b-4a2c-8af8-640b73809499)



## Reports and Analytics

The system provides several analytics views:
- **Inventory Overview**: Current stock distribution
- **Sales Trends**: Daily and monthly sales patterns
- **Category Analysis**: Sales and inventory by category
- **Expiry Tracking**: Upcoming expiries and expired items

## Dark Mode Support

The application supports both light and dark themes, which can be toggled via the user interface.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Flask for the web framework
- Bootstrap for the frontend components
- Chart.js for data visualization
- SQLAlchemy for database management
