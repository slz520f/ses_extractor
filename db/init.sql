CREATE TABLE IF NOT EXISTS ses_projects (
    id SERIAL PRIMARY KEY,
    received_at TIMESTAMP,
    subject TEXT,
    sender_email VARCHAR(255),
    project_description TEXT,
    required_skills TEXT,
    optional_skills TEXT,
    location TEXT,
    unit_price VARCHAR(100),
    message_id VARCHAR(255) UNIQUE,
    is_parsed BOOLEAN DEFAULT FALSE,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);