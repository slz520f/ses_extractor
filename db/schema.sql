CREATE TABLE ses_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    received_at DATETIME,
    subject TEXT,
    sender_email VARCHAR(255),
    project_description TEXT,
    required_skills TEXT,
    optional_skills TEXT,
    location TEXT,
    unit_price VARCHAR(100),
    message_id VARCHAR(255) UNIQUE,  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
