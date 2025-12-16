import os
import psycopg2
from urllib.parse import urlparse
from psycopg2 import extras 

# --- PostgreSQL Connection Setup ---
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://daa_management_system_user:TTHSPLg694Qxw8rd6uRraRk9Bh8SirWn@dpg-d4vshipr0fns739s6gk0-a/daa_management_system"
)

# Define table names
TABLE_NAME_ADMIN = "administrators"
TABLE_NAME_STUDENT = "students"
TABLE_NAME_TEACHER = "teachers"
TABLE_NAME_PARENT = "parents"
TABLE_NAME_STUDENT_DATA = "student_data"
TABLE_NAME_SCHEDULE = "schedules_table"
TABLE_NAME_SUBJECT = "subjects"
TABLE_NAME_FEES = "fees"
TABLE_NAME_STUDENT_SUBJECTS = "student_subjects"

def get_connection_details():
    """Parses the DATABASE_URL into a dictionary for psycopg2.connect."""
    url = urlparse(DATABASE_URL)
    return {
        "dbname": url.path[1:],
        "user": url.username,
        "password": url.password,
        "host": url.hostname,
        "port": url.port
    }

DB_CONN_DETAILS = get_connection_details()

def init_db():
    """Initializes the PostgreSQL database and creates all tables with lowercase identifiers."""
    conn = None
    try:
        print("Attempting to connect to the database...")
        conn = psycopg2.connect(**DB_CONN_DETAILS)
        conn.autocommit = True
        cursor = conn.cursor()

        # Drop tables in reverse order (optional, for clean re-initialization)
        # cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME_FEES}, {TABLE_NAME_STUDENT_SUBJECTS}, {TABLE_NAME_SCHEDULE}, {TABLE_NAME_SUBJECT}, {TABLE_NAME_STUDENT}, {TABLE_NAME_TEACHER}, {TABLE_NAME_ADMIN} CASCADE;")
        # print("Existing tables dropped.")
        
        # ADMINS (id, name, password)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_ADMIN} (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            );
        """)
        # Insert initial admin if none exists
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_ADMIN}")
        if cursor.fetchone()[0] == 0:
             cursor.execute(f"""
                INSERT INTO {TABLE_NAME_ADMIN} (name, password) VALUES ('admin', 'admin')
            """)
             print("Initial admin created (user: admin, pass: admin).")

        # STUDENTS (id, name, gender, class, grade, password, phone)
        # Using a single table for simplicity, but named 'students'
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_STUDENT} (
                id INT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                gender VARCHAR(50),
                class VARCHAR(50),
                grade VARCHAR(50),
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(50)
            );
        """)

        # TEACHERS (id, name, gender, password, phone)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_TEACHER} (
                id INT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                gender VARCHAR(50),
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(50)
            );
        """)

        # SUBJECTS (subject_id, name, teacher_id)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_SUBJECT} (
                subject_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                teacher_id INT,
                CONSTRAINT fk_teacher FOREIGN KEY (teacher_id) 
                    REFERENCES {TABLE_NAME_TEACHER} (id) ON DELETE SET NULL ON UPDATE CASCADE
            );
        """)
        
        # SCHEDULES (schedule_id, subject_id, day_of_week, class_time)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_SCHEDULE} (
                schedule_id SERIAL PRIMARY KEY,
                subject_id INT NOT NULL,
                day_of_week VARCHAR(20) NOT NULL,
                class_time TIME NOT NULL,
                UNIQUE (subject_id, day_of_week, class_time),
                CONSTRAINT fk_schedule_subject FOREIGN KEY (subject_id) 
                    REFERENCES {TABLE_NAME_SUBJECT} (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)

        # STUDENT_SUBJECTS (student_id, subject_id) - Enrollment mapping
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_STUDENT_SUBJECTS} (
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                PRIMARY KEY (student_id, subject_id),
                CONSTRAINT fk_ss_student FOREIGN KEY (student_id) 
                    REFERENCES {TABLE_NAME_STUDENT} (id) ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_ss_subject FOREIGN KEY (subject_id) 
                    REFERENCES {TABLE_NAME_SUBJECT} (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)

        # FEES (fee_id, student_id, subject_id, amount, paid, status, due_date)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_FEES} (
                fee_id SERIAL PRIMARY KEY,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                paid DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(50) CHECK (status IN ('pending', 'partial', 'paid')) DEFAULT 'pending',
                due_date DATE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (student_id, subject_id),
                CONSTRAINT fk_fee_student FOREIGN KEY (student_id) 
                    REFERENCES {TABLE_NAME_STUDENT} (id) ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_fee_subject FOREIGN KEY (subject_id) 
                    REFERENCES {TABLE_NAME_SUBJECT} (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)

        cursor.close()
        print("Database initialized successfully with PostgreSQL tables and lowercase columns.")
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db()
