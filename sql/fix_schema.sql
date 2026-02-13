CREATE TABLE customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    jump_host BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jump_host_ip VARCHAR(45),
    jump_host_username VARCHAR(255),
    jump_host_password VARCHAR(255),
    image LONGBLOB
);

CREATE TABLE devices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    serial_number VARCHAR(50) NOT NULL,
    device_type VARCHAR(100) NOT NULL,
    device_model VARCHAR(255) NOT NULL,
    device_ip VARCHAR(45) NOT NULL,
    device_username VARCHAR(255) NOT NULL,
    device_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(id)
        ON DELETE CASCADE,
    INDEX (customer_id)
);

CREATE TABLE command_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    command TEXT NOT NULL,
    customer_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jump_host BOOLEAN DEFAULT FALSE,
    general_description TEXT
    
    FOREIGN KEY (customer_id) REFERENCES customers(id)
        ON DELETE CASCADE,
    INDEX (customer_id)
);

CREATE TABLE reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    customer_id INT NOT NULL,
    template_id INT NOT NULL,
    result LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (device_id) REFERENCES devices(id)
        ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES command_templates(id)
        ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
        ON DELETE CASCADE,

    INDEX (device_id),
    INDEX (template_id),
    INDEX (customer_id)
);








