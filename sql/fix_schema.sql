CREATE DATABASE IF NOT EXISTS reportingapp;
USE reportingapp;

-- Customers
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    jump_host TINYINT(1) DEFAULT 0,
    jump_host_ip VARCHAR(45),
    jump_host_username VARCHAR(255),
    jump_host_password VARCHAR(255),
    jump_host_hostname VARCHAR(255),
    device_type VARCHAR(100),
    jump_port INT DEFAULT 22,
    images LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devices
CREATE TABLE devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    serial_number VARCHAR(50),
    hostname VARCHAR(50),
    device_type VARCHAR(100) NOT NULL,
    device_model VARCHAR(255) NOT NULL,
    device_ip VARCHAR(45) NOT NULL,
    device_port INT DEFAULT 22,
    username VARCHAR(255),
    password VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Command Templates
CREATE TABLE command_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description JSON,
    command JSON,
    customer_id INT NOT NULL,
    general_desc TEXT,
    premade_report BOOLEAN DEFAULT FALSE,
    manual_summary_desc TEXT,
    manual_summary_table JSON,
    company_logo LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Reports
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    customer_id INT NOT NULL,
    template_id INT NOT NULL,
    result LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ai_summary BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES command_templates(id) ON DELETE CASCADE
);

-- Users (for authentication)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    is_admin TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
