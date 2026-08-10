ALTER TABLE users ADD COLUMN company_id VARCHAR(100) DEFAULT 'default-company';

CREATE TABLE custom_document_keyword (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(100) NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);