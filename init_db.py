import os
import psycopg2
from urllib.parse import urlparse

# --- PostgreSQL Connection Setup ---
# The DATABASE_URL is required by Render and is used here.
# For local testing, you must set this environment variable or modify this file.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://daa_management_system_user:TTHSPLg694Qxw8rd6uRraRk9Bh8SirWn@dpg-d4vshipr0fns739s6gk0-a/daa_management_system"
)

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
    """Initializes the PostgreSQL database and creates all tables."""
    conn = None
    try:
        # Connect to the specific database
        conn = psycopg2.connect(**DB_CONN_DETAILS)
        conn.autocommit = True  # Ensure DDL (CREATE TABLE) commands commit immediately
        cursor = conn.cursor()

        # Define table names
        TABLE_NAME_ADMIN = "administrators"
        TABLE_NAME_STUDENT = "students"
        TABLE_NAME_TEACHER = "teachers"
        TABLE_NAME_PARENT = "parents"
        TABLE_NAME_STUDENT_DATA = "student_data"
        TABLE_NAME_SCHEDULE = "schedules_table"
        TABLE_NAME_SUBJECT = "subjects"

        # --- Table Creation (PostgreSQL Dialect) ---

        # PostgreSQL uses SERIAL for auto-increment and TEXT for non-fixed-length strings

        # ADMINISTRATORS
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_ADMIN} (
                "ID" SERIAL PRIMARY KEY,
                "Name" VARCHAR(255) NOT NULL,
                "Password" VARCHAR(255) NOT NULL
            );
        """)

        # STUDENTS
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_STUDENT} (
                "ID" SERIAL PRIMARY KEY,
                "Name" VARCHAR(255) NOT NULL,
                "Password" VARCHAR(255) NOT NULL,
                "Phone" VARCHAR(50),
                "Gender" VARCHAR(50) CHECK ("Gender" IN ('male','female','other')) DEFAULT 'other'
            );
        """)

        # TEACHERS
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_TEACHER} (
                "ID" SERIAL PRIMARY KEY,
                "Name" VARCHAR(255) NOT NULL,
                "Password" VARCHAR(255) NOT NULL,
                "Phone" VARCHAR(50),
                "Gender" VARCHAR(50) CHECK ("Gender" IN ('male','female','other')) DEFAULT 'other'
            );
        """)

        # PARENTS
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_PARENT} (
                "ID" SERIAL PRIMARY KEY,
                "Password" VARCHAR(255) NOT NULL,
                "ChildrentID" INT,
                CONSTRAINT fk_parent_child FOREIGN KEY ("ChildrentID")
                    REFERENCES {TABLE_NAME_STUDENT} ("ID")
                    ON DELETE SET NULL ON UPDATE CASCADE
            );
        """)

        # STUDENT_DATA (Removed redundant trigger logic by creating a VIEW or a different structure, 
        # but maintaining the table structure for minimal change)
        # Note: The original MySQL triggers are replaced with a simpler INSERT/UPDATE/DELETE structure
        # or would be best handled by a view/single table in a pure relational design.
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_STUDENT_DATA} (
                "ID" INT PRIMARY KEY,
                "Name" VARCHAR(255) NOT NULL,
                "Gender" VARCHAR(50) CHECK ("Gender" IN ('male','female','other')) DEFAULT 'other',
                "Class" VARCHAR(50),
                "Grade" VARCHAR(10),
                "Password" VARCHAR(255) NOT NULL,
                "Phone" VARCHAR(50),
                CONSTRAINT fk_student_data FOREIGN KEY ("ID")
                    REFERENCES {TABLE_NAME_STUDENT} ("ID")
                    ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)
        
        # SCHEDULES_TABLE
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_SCHEDULE} (
                schedule_id SERIAL PRIMARY KEY,
                "ID" INT NOT NULL,
                "Name" VARCHAR(255),
                "Terms" VARCHAR(100),
                "Subject" VARCHAR(255) NOT NULL,
                "Day" VARCHAR(20) NOT NULL,
                Time_start TIME WITHOUT TIME ZONE NOT NULL,
                Time_end TIME WITHOUT TIME ZONE NOT NULL,
                CONSTRAINT fk_schedule_teacher FOREIGN KEY ("ID") 
                    REFERENCES {TABLE_NAME_TEACHER} ("ID") 
                    ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)

        # SUBJECTS
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_SUBJECT} (
                subject_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                teacher_id INT,
                CONSTRAINT fk_subject_teacher FOREIGN KEY (teacher_id) 
                    REFERENCES {TABLE_NAME_TEACHER} ("ID") 
                    ON DELETE SET NULL ON UPDATE CASCADE
            );
        """)

        # FEES
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS fees (
                fee_id SERIAL PRIMARY KEY,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                paid DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(50) CHECK (status IN ('pending', 'partial', 'paid')) DEFAULT 'pending',
                due_date DATE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_fee_student FOREIGN KEY (student_id) REFERENCES {TABLE_NAME_STUDENT} ("ID") 
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_fee_subject FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)

        # STUDENT_SUBJECTS
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS student_subjects (
                enrollment_id SERIAL PRIMARY KEY,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                enrolled_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (student_id, subject_id),
                CONSTRAINT fk_enrollment_student FOREIGN KEY (student_id) 
                    REFERENCES {TABLE_NAME_STUDENT} ("ID") ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_enrollment_subject FOREIGN KEY (subject_id) 
                    REFERENCES subjects (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
            );
        """)
        cursor.close()

        print("Database initialized successfully with PostgreSQL.")
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # You would typically run this on your local machine or as part of a pre-deploy hook.
    init_db()
