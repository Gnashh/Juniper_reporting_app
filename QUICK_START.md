# 🚀 Quick Start - Authentication Setup

## 3-Minute Setup

### 1️⃣ Install bcrypt (30 seconds)
```bash
pip install bcrypt==4.0.1
```

### 2️⃣ Run setup script (1 minute)
```bash
cd Juniper_reporting_app
python setup_auth.py
```

Expected output:
```
✅ Users table created successfully
✅ Default admin user created successfully!
   Username: admin
   Password: admin123
```

### 3️⃣ Start the app (30 seconds)
```bash
streamlit run app.py
```

### 4️⃣ Login (30 seconds)
- Open browser (usually auto-opens at http://localhost:8501)
- Username: `admin`
- Password: `admin123`
- Click "Login"

### 5️⃣ Change password (30 seconds)
1. Click "User Management" in sidebar
2. Select admin user (checkbox)
3. Click "🔑 Change Password"
4. Enter new password (twice)
5. Click "✅ Change Password"

## ✅ Done!

You now have a fully authenticated Streamlit app!

## 📋 What You Get

✅ Login page with username/password
✅ Secure password hashing (bcrypt)
✅ Session management
✅ User management interface (admin only)
✅ Logout functionality
✅ Role-based access control

## 🎯 Common Tasks

### Create a New User
1. Login as admin
2. Go to "User Management"
3. Click "➕ Add User"
4. Fill in details
5. Check "Administrator" if needed
6. Click "✅ Submit"

### Change Any User's Password
1. Login as admin
2. Go to "User Management"
3. Select user (checkbox)
4. Click "🔑 Change Password"
5. Enter new password
6. Click "✅ Change Password"

### Delete a User
1. Login as admin
2. Go to "User Management"
3. Select user(s) (checkbox)
4. Click "🗑 Delete User"
5. Confirm deletion

### Logout
- Click "🚪 Logout" button in sidebar

## 🐛 Troubleshooting

### Problem: "Module 'bcrypt' not found"
**Solution:**
```bash
pip install bcrypt==4.0.1
```

### Problem: "Table 'users' doesn't exist"
**Solution:**
```bash
python setup_auth.py
```

### Problem: Can't login with admin/admin123
**Solution:**
1. Check database connection in `.env`
2. Run setup script again:
   ```bash
   python setup_auth.py
   ```
3. Test authentication:
   ```bash
   python test_auth.py
   ```

### Problem: User Management not showing
**Solution:**
- Make sure you're logged in as admin
- Check database: `SELECT * FROM users WHERE username='admin'`
- Verify `is_admin` field is `1` or `TRUE`

## 📚 More Information

- **Detailed Guide:** [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md)
- **Implementation Details:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Main README:** [README.md](README.md)

## 💡 Pro Tips

1. **Use Strong Passwords**
   - Minimum 12 characters
   - Mix uppercase, lowercase, numbers, symbols

2. **Limit Admin Access**
   - Only make trusted users admins
   - Regular users can still use all features

3. **Regular Backups**
   - Backup your users table regularly
   - Export: `mysqldump -u user -p database users > users_backup.sql`

4. **Monitor Activity**
   - Check `last_login` field in users table
   - Deactivate unused accounts

## 🎉 Success!

Your app is now secure with authentication!

**Default Credentials:**
- Username: `admin`
- Password: `admin123` (⚠️ Change this!)

**Next Steps:**
1. ✅ Change default password
2. ✅ Create user accounts for your team
3. ✅ Start using the app!

---

Need help? Check the detailed documentation in [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md)

