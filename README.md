# Juniper_reporting_app

A Streamlit-based reporting application for Juniper network devices with built-in authentication.

## 🚀 Setup Instructions

### 1. Clone the repository

### 2. Install dependencies
```bash
pip install -r requirements
```

### 3. Configure Database
- Copy `.env.example` to `.env`
- Update `.env` with your actual database credentials

### 4. Setup Authentication
Run the authentication setup script:
```bash
python setup_auth.py
```

This will:
- Create the users table
- Add a default admin user (username: `admin`, password: `admin123`)

### 5. Run the app
```bash
streamlit run app.py
```

### 6. First Login
- Login with username: `admin`, password: `admin123`
- **Important:** Change the default password immediately!

## 🔐 Authentication

This app includes a complete authentication system:

- **Login/Logout** - Secure user authentication
- **User Management** - Admin interface for managing users
- **Role-Based Access** - Admin and regular user roles
- **Password Security** - Bcrypt password hashing

For detailed authentication documentation, see [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md)

## 📋 Features

- Customer management
- Device management
- Template management
- Report generation and PDF export
- User authentication and management
- Role-based access control

## Environment Variables

See `.env.example` for required environment variables.



