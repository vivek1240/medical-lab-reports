CREATE TABLE IF NOT EXISTS biomarker_reference (
    id INT AUTO_INCREMENT PRIMARY KEY,
    standard_name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    common_aliases TEXT NOT NULL,
    typical_unit VARCHAR(50),
    typical_range_male VARCHAR(100),
    typical_range_female VARCHAR(100),
    INDEX idx_biomarker_category (category)
);

CREATE TABLE IF NOT EXISTS lab_reports (
    doc_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    patient_name VARCHAR(255) NOT NULL,
    patient_id VARCHAR(50),
    date_of_birth DATE,
    gender VARCHAR(20),
    lab_name VARCHAR(255),
    report_date DATE,
    collection_date DATE,
    sample_type VARCHAR(100),
    physician_name VARCHAR(255),
    original_filename VARCHAR(255),
    raw_parsed_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lab_reports_user_id (user_id),
    INDEX idx_lab_reports_report_date (report_date)
);

CREATE TABLE IF NOT EXISTS test_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    doc_id VARCHAR(36) NOT NULL,
    biomarker_id INT NULL,
    test_name VARCHAR(255) NOT NULL,
    value VARCHAR(50),
    unit VARCHAR(50),
    reference_range VARCHAR(100),
    category VARCHAR(100),
    flag VARCHAR(20),
    FOREIGN KEY (doc_id) REFERENCES lab_reports(doc_id) ON DELETE CASCADE,
    FOREIGN KEY (biomarker_id) REFERENCES biomarker_reference(id) ON DELETE SET NULL,
    INDEX idx_test_results_doc_id (doc_id),
    INDEX idx_test_results_test_name (test_name),
    INDEX idx_test_results_biomarker_id (biomarker_id)
);
