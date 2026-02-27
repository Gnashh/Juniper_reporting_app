# Authentication Setup Guide

This guide explains how to set up and use the authentication system in the Juniper Reporting App.

## 🚀 Quick Start

### 1. Install Dependencies

First, install the required bcrypt package:

```bash
pip install bcrypt==4.0.1
```

Or install all dependencies:

```bash
pip install -r dependencies
```

### 2. Create Users Table

Run the SQL script to create the users table in your database:

```bash
mysql -u your_username -p your_database < sql/create_users_table.sql
```

Or manually execute the SQL:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email)
);
```

### 3. Insert Default Admin User

The SQL script automatically creates a default admin user:

- **Username:** `admin`
- **Password:** `admin123`

⚠️ **IMPORTANT:** Change this password immediately after first login!

## 📋 Features

### ✅ Implemented Features

1. **Login System**
   - Username/password authentication
   - Secure password hashing with bcrypt
   - Session management
   - Last login tracking

2. **User Management (Admin Only)**
   - Create new users
   - Delete users
   - Change user passwords
   - View all users
   - Assign admin privileges

3. **Role-Based Access**
   - Admin users can access User Management
   - Regular users have standard access
   - Protected routes

4. **Security Features**
   - Password hashing with bcrypt
   - Session-based authentication
   - Logout functionality
   - Password strength validation (minimum 6 characters)

## 🔐 Usage

### Logging In

1. Run the app: `streamlit run app.py`
2. You'll be redirected to the login page
3. Enter your credentials
4. Click "Login"

### Managing Users (Admin Only)

1. Login as an admin user
2. Navigate to "User Management" in the sidebar
3. Use the interface to:
   - Add new users
   - Change passwords
   - Delete users (except yourself)

### Logging Out

Click the "🚪 Logout" button in the sidebar.

## 🛠️ Customization

### Adding Custom User Fields

Edit `db/users.py` to add custom fields to the user model.

### Changing Password Requirements

Edit the validation in `user_management.py`:

```python
if len(password) < 6:  # Change minimum length here
    st.error("Password must be at least 6 characters")
    return
```

### Customizing Login Page

Edit `auth.py` in the `show_login_page()` function to customize the login UI.

## 🔧 API Reference

### Authentication Functions (`auth.py`)

- `check_authentication()` - Check if user is authenticated
- `login_user(username, password)` - Authenticate and login user
- `logout_user()` - Logout current user
- `get_current_user()` - Get current user info
- `is_admin()` - Check if current user is admin
- `require_authentication()` - Enforce authentication (use at app start)

### User Management Functions (`db/users.py`)

- `create_user(username, password, full_name, email, is_admin)` - Create new user
- `authenticate_user(username, password)` - Verify credentials
- `get_user_by_id(user_id)` - Get user by ID
- `get_user_by_username(username)` - Get user by username
- `get_all_users()` - Get all users
- `update_user(user_id, ...)` - Update user info
- `change_password(user_id, new_password)` - Change password
- `delete_user(user_id)` - Delete user

## 🔒 Security Best Practices

1. **Change Default Password**
   - Immediately change the default admin password after setup

2. **Use Strong Passwords**
   - Minimum 8-12 characters recommended
   - Mix of uppercase, lowercase, numbers, and symbols

3. **Regular Password Updates**
   - Encourage users to update passwords regularly

4. **Limit Admin Access**
   - Only grant admin privileges to trusted users

5. **Database Security**
   - Keep your `.env` file secure
   - Never commit `.env` to version control
   - Use strong database passwords

## 🐛 Troubleshooting

### "Module 'bcrypt' not found"
```bash
pip install bcrypt==4.0.1
```

### "Table 'users' doesn't exist"
Run the SQL script to create the users table.

### "Invalid username or password"
- Check username spelling (case-sensitive)
- Verify password is correct
- Ensure user is active in database

### Can't access User Management
- Verify you're logged in as an admin user
- Check `is_admin` field in database

## 📝 Database Schema

```sql
users
├── id (INT, PRIMARY KEY, AUTO_INCREMENT)
├── username (VARCHAR(50), UNIQUE, NOT NULL)
├── password_hash (VARCHAR(255), NOT NULL)
├── full_name (VARCHAR(100))
├── email (VARCHAR(100))
├── is_active (BOOLEAN, DEFAULT TRUE)
├── is_admin (BOOLEAN, DEFAULT FALSE)
├── created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
└── last_login (TIMESTAMP, NULL)
```

## 🎯 Next Steps

1. Change the default admin password
2. Create user accounts for your team
3. Test the login/logout functionality
4. Customize the authentication flow as needed

