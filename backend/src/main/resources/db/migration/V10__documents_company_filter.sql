ALTER TABLE documents ADD COLUMN company_id VARCHAR(100) DEFAULT 'default-company';

UPDATE documents SET company_id = 'default-company' WHERE company_id IS NULL;