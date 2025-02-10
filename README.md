# Modern Café Management System

A modern, responsive web application for managing a café's menu, orders, and customer interactions. Built with Flask and designed with a beautiful coffee-themed UI.

## Features

### Customer Features
- 🍽️ Browse menu items by category (Coffee, Tea, Desserts)
- 🛒 Shopping cart functionality
- 👤 User registration and authentication
- 📱 Phone number verification system
- 📊 Order tracking and history
- 🔐 Password management

### Admin Features
- 📋 Product management (Add, Edit, Delete)
- 📦 Stock management
- 👥 User management
- 📈 Sales and revenue reports
- 🛍️ Order management system
- 💰 Revenue tracking and analytics

## Technology Stack

- **Backend**: Python/Flask
- **Database**: SQLite with SQLAlchemy
- **Frontend**: 
  - HTML5/CSS3
  - JavaScript
  - Bootstrap 5
  - Font Awesome icons
- **Authentication**: Flask-Login
- **Security**: Werkzeug security

## Installation

1. Clone the repository: 

`https://github.com/Good-Wizard/cafe-management.git` then `cd cafe-management`


6. Run the application:

`python main.py`


## Project Structure

```
cafe-management/
├── static/
│   ├── css/
│   │   └── style.css
│   └── uploads/
├── templates/
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── products.html
│   │   └── ...
│   ├── base.html
│   ├── home.html
│   └── ...
├── main.py
└── README.md
```

## Database Schema

- **Users**: Store customer and admin information
- **Products**: Menu items with categories
- **Orders**: Customer orders with status tracking
- **OrderItems**: Individual items in each order
- **CartItems**: Shopping cart functionality

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## Acknowledgments

- Font Awesome for icons
- Bootstrap team for the amazing framework
- Google Fonts for beautiful typography

## Contact

Arash Rahbar - [@arash.rahbar83](https://instagram.com/arash.rahbar83)

Project Link: [https://github.com/Good-Wizard/cafe-management.git](https://github.com/Good-Wizard/cafe-management.git)