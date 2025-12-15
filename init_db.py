import psycopg2
from urllib.parse import urlparse
import os
import sys
from contextlib import contextmanager

# --- CONFIGURATION (Repeated here to run independently) ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("FATAL: DATABASE_URL environment variable is not set! Cannot initialize database.")
    sys.exit(1) 

URL_PARTS = urlparse(DATABASE_URL)
DB_CONF = {
    "host": URL_PARTS.hostname,
    "database": URL_PARTS.path[1:],
    "user": URL_PARTS.username,
    "password": URL_PARTS.password,
    "port": URL_PARTS.port
}

# --- Table Names (AS REQUESTED) ---
TABLE_NAME_ADMIN = "administrators"
TABLE_NAME_STUDENT = "students"
TABLE_NAME_TEACHER = "teachers"
TABLE_NAME_PARENT = "parents"
TABLE_NAME_STUDENT_DATA = "student_data"
TABLE_NAME_SCHEDULE = "schedules_table"
TABLE_NAME_SUBJECT = "subjects"

@contextmanager
def get_db_conn():
    """Context manager for database connection used only by the initialization script."""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONF)
        cursor = conn.cursor()
        yield conn, cursor
    except Exception as e:
        print("Database connection error in init_db:", e)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def init_db():
    """Initialize database schema for PostgreSQL."""
    try:
        with get_db_conn() as (conn, cursor):
            print("Attempting to initialize database schema...")
            
            # 1. Define ENUM types
            cursor.execute("DROP TYPE IF EXISTS gender_type CASCADE;")
            cursor.execute("CREATE TYPE gender_type AS ENUM ('male', 'female', 'other');")

            cursor.execute("DROP TYPE IF EXISTS fee_status_type CASCADE;")
            cursor.execute("CREATE TYPE fee_status_type AS ENUM ('pending', 'partial', 'paid');")

            # 2. Create tables
            # Administrators
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME_ADMIN} (
                    ID SERIAL PRIMARY KEY,
                    Name VARCHAR(255) NOT NULL UNIQUE,
                    Password VARCHAR(255) NOT NULL
                );
            """)
            
            # Teachers
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME_TEACHER} (
                    ID SERIAL PRIMARY KEY,
                    Name VARCHAR(255) NOT NULL UNIQUE,
                    Password VARCHAR(255) NOT NULL,
                    Phone VARCHAR(50),
                    Gender gender_type DEFAULT 'other'
                );
            """)

            # Students (Using the TABLE_NAME_STUDENT_DATA as the primary table for records)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME_STUDENT_DATA} (
                    ID SERIAL PRIMARY KEY,
                    Name VARCHAR(255) NOT NULL,
                    Gender gender_type DEFAULT 'other',
                    Class VARCHAR(50),
                    Grade VARCHAR(10),
                    Password VARCHAR(255) NOT NULL,
                    Phone VARCHAR(50)
                );
            """)
            
            # Parents (ChildrentID references student_data ID)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME_PARENT} (
                    ID SERIAL PRIMARY KEY,
                    Password VARCHAR(255) NOT NULL,
                    ChildrentID INT,
                    CONSTRAINT fk_parent_child FOREIGN KEY (ChildrentID)
                        REFERENCES {TABLE_NAME_STUDENT_DATA} (ID)
                        ON DELETE SET NULL ON UPDATE CASCADE
                );
            """)

            # Subjects (teacher_id references teachers ID)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME_SUBJECT} (
                    subject_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    teacher_id INT,
                    CONSTRAINT fk_subject_teacher FOREIGN KEY (teacher_id)
                        REFERENCES {TABLE_NAME_TEACHER} (ID)
                        ON DELETE SET NULL ON UPDATE CASCADE
                );
            """)

            # Schedules (ID references teacher ID)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME_SCHEDULE} (
                    schedule_id SERIAL PRIMARY KEY,
                    ID INT NOT NULL, -- Teacher ID
                    Name VARCHAR(255),
                    Terms VARCHAR(100),
                    Subject VARCHAR(255) NOT NULL,
                    Day VARCHAR(20) NOT NULL,
                    Time_start TIME NOT NULL,
                    Time_end TIME NOT NULL,
                    CONSTRAINT fk_schedule_teacher FOREIGN KEY (ID)
                        REFERENCES {TABLE_NAME_TEACHER} (ID)
                        ON DELETE CASCADE ON UPDATE CASCADE
                );
            """)
            
            # Student Subjects (Enrollment)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS student_subjects (
                    enrollment_id SERIAL PRIMARY KEY,
                    student_id INT NOT NULL,
                    subject_id INT NOT NULL,
                    enrolled_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_enrollment UNIQUE (student_id, subject_id),
                    CONSTRAINT fk_enrollment_student FOREIGN KEY (student_id) 
                        REFERENCES {TABLE_NAME_STUDENT_DATA} (ID) ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT fk_enrollment_subject FOREIGN KEY (subject_id) 
                        REFERENCES {TABLE_NAME_SUBJECT} (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
                );
            """)
            
            # Fees
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS fees (
                    fee_id SERIAL PRIMARY KEY,
                    student_id INT NOT NULL,
                    subject_id INT NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    paid DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    status fee_status_type DEFAULT 'pending',
                    due_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_fee UNIQUE (student_id, subject_id),
                    CONSTRAINT fk_fee_student FOREIGN KEY (student_id)
                        REFERENCES {TABLE_NAME_STUDENT_DATA} (ID) ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT fk_fee_subject FOREIGN KEY (subject_id)
                        REFERENCES {TABLE_NAME_SUBJECT} (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
                );
            """)

            conn.commit()
            print("Database schema initialized successfully.")

    except Exception as e:
        print("FATAL: Database initialization failed:", e)
        raise

if __name__ == '__main__':
    try:
        init_db()
    except Exception:
        sys.exit(1)
