from flask import Flask, render_template, request, redirect, url_for, flash, session
# Use psycopg2 for PostgreSQL
import psycopg2
from urllib.parse import urlparse
import os
from contextlib import contextmanager

app = Flask(__name__)
# It's better to load the secret key from an environment variable in production
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Load the database URL from the environment variable provided by Render
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Parse the database URL
URL_PARTS = urlparse(DATABASE_URL)
DB_CONF = {
    "host": URL_PARTS.hostname,
    "database": URL_PARTS.path[1:],
    "user": URL_PARTS.username,
    "password": URL_PARTS.password,
    "port": URL_PARTS.port
}

# --- Table Names (Keep the same for consistency) ---
# NOTE: The students table is effectively replaced by student_data
# for simplicity and to avoid complex trigger logic in the transition.
DB_NAME = "daa_management_system" # Not strictly used with connection string
TABLE_NAME_ADMIN = "administrators"
TABLE_NAME_STUDENT_DATA = "student_data" # Used as the main student table
TABLE_NAME_TEACHER = "teachers"
TABLE_NAME_PARENT = "parents"
TABLE_NAME_SCHEDULE = "schedules_table"
TABLE_NAME_SUBJECT = "subjects"
TABLE_NAME_STUDENT = TABLE_NAME_STUDENT_DATA # Point student-related logic here

@contextmanager
def get_db_conn(dict_cursor=False):
    """Context manager for database connection."""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONF)
        # For dictionary cursor, we use RealDictCursor
        if dict_cursor:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        yield conn, cursor
    except Exception as e:
        # In a real app, you would log this error
        print("Database connection error:", e)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def init_db():
    """Initialize database schema for PostgreSQL."""
    conn = None
    cursor = None
    try:
        with get_db_conn() as (conn, cursor):
            # 1. Define ENUM types for Gender and Fee Status
            # Safely create the type if it doesn't exist
            cursor.execute("DROP TYPE IF EXISTS gender_type CASCADE;")
            cursor.execute("CREATE TYPE gender_type AS ENUM ('male', 'female', 'other');")

            cursor.execute("DROP TYPE IF EXISTS fee_status_type CASCADE;")
            cursor.execute("CREATE TYPE fee_status_type AS ENUM ('pending', 'partial', 'paid');")

            # 2. Create tables
            # ID will be SERIAL (auto-increment in PostgreSQL)

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

            # Students (Using student_data as the primary student table)
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
                        REFERENCES subjects (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
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
                        REFERENCES subjects (subject_id) ON DELETE CASCADE ON UPDATE CASCADE
                );
            """)

            conn.commit()

    except Exception as e:
        print("Database initialization error:", e)
        # Reraise the exception to stop the application startup if the DB is unavailable/misconfigured
        raise


# --- ROLE_TEMPLATES and SIGNUP_TEMPLATES remain the same ---
ROLE_TEMPLATES = {
    'administrator': 'login/administrators.html',
    'teacher': 'login/teachers.html',
    'student': 'login/students.html',
    'parent': 'login/parents.html'
}

SIGNUP_TEMPLATES = {
    'administrator': 'sig in/create_admin.html',
    'teacher': 'sign in/create_teacher.html',
    'student': 'sign in/create_student.html',
    'parent': 'sign in/create_parent.html'
}

@app.route('/')
def index():
    return render_template('index.html')

# --- Login/Signup Routes (Updated for psycopg2 and table names) ---

@app.route('/administrators', methods=['GET', 'POST'])
def administrators_page():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('administrators_page'))
        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute(f"SELECT ID, Name, Password FROM {TABLE_NAME_ADMIN} WHERE Name=%s", (name,))
                row = cursor.fetchone()
            if not row or password != row[2]:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('administrators_page'))
            session['user_name'] = row[1]
            session['user_role'] = 'administrator'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('administrators_page'))
    return render_template('login/administrators.html')

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('create_admin'))
        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute(
                    f"INSERT INTO {TABLE_NAME_ADMIN} (Name, Password) VALUES (%s, %s)",
                    (name, password)
                )
                conn.commit()
            flash('Administrator account created. You can now sign in.', 'success')
            return redirect(url_for('administrators_page'))
        except psycopg2.errors.UniqueViolation:
            flash('Record already exists (duplicate name).', 'error')
            return redirect(url_for('create_admin'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_admin'))
    return render_template('sign in/create_admin.html')

# ... (Teachers, Students, Parents pages are similar, just changing the DB connection and error handling) ...

@app.route('/teachers', methods=['GET', 'POST'])
def teachers_page():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('teachers_page'))
        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute(f"SELECT ID, Name, Password FROM {TABLE_NAME_TEACHER} WHERE Name=%s", (name,))
                row = cursor.fetchone()
            if not row or password != row[2]:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('teachers_page'))
            session['user_name'] = row[1]
            session['user_role'] = 'teacher'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('teachers_page'))
    return render_template('login/teachers.html')

@app.route('/create_teacher', methods=['GET', 'POST'])
def create_teacher():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip() or None
        gender = request.form.get('gender', '').strip().lower() or 'other'
        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('create_teacher'))
        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute(
                    f"INSERT INTO {TABLE_NAME_TEACHER} (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                    (name, password, phone, gender)
                )
                conn.commit()
            flash('Teacher account created. You can now sign in.', 'success')
            return redirect(url_for('teachers_page'))
        except psycopg2.errors.UniqueViolation:
            flash('Record already exists (duplicate name).', 'error')
            return redirect(url_for('create_teacher'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_teacher'))
    return render_template('sign in/create_teacher.html')

@app.route('/students', methods=['GET', 'POST'])
def students_page():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('students_page'))
        try:
            # Note: TABLE_NAME_STUDENT now points to TABLE_NAME_STUDENT_DATA
            with get_db_conn() as (conn, cursor):
                cursor.execute(f"SELECT ID, Name, Password FROM {TABLE_NAME_STUDENT} WHERE Name=%s", (name,))
                row = cursor.fetchone()
            if not row or password != row[2]:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('students_page'))
            session['user_name'] = row[1]
            session['user_role'] = 'student'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('students_page'))
    return render_template('login/students.html')

@app.route('/create_student', methods=['GET', 'POST'])
def create_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip() or None
        gender = request.form.get('gender', '').strip().lower() or 'other'
        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('create_student'))
        try:
            # Note: Inserting directly into student_data (formerly TABLE_NAME_STUDENT)
            with get_db_conn() as (conn, cursor):
                cursor.execute(
                    f"INSERT INTO {TABLE_NAME_STUDENT} (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                    (name, password, phone, gender)
                )
                conn.commit()
            flash('Student account created. You can now sign in.', 'success')
            return redirect(url_for('students_page'))
        except psycopg2.errors.UniqueViolation:
            flash('Record already exists (duplicate name).', 'error')
            return redirect(url_for('create_student'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_student'))
    return render_template('sig in/create_student.html')


@app.route('/parents', methods=['GET', 'POST'])
def parents_page():
    if request.method == 'POST':
        pid = request.form.get('name', '').strip() # Parent ID is used as 'name'
        password = request.form.get('password', '').strip()
        if not (pid and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('parents_page'))
        try:
            parent_id = int(pid)
        except ValueError:
            flash('Parent ID must be a number.', 'error')
            return redirect(url_for('parents_page'))

        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute(f"SELECT ID, Password FROM {TABLE_NAME_PARENT} WHERE ID=%s", (parent_id,))
                row = cursor.fetchone()
            if not row or password != row[1]:
                flash('Invalid Parent ID or password.', 'error')
                return redirect(url_for('parents_page'))

            session['user_name'] = f"Parent#{row[0]}"
            session['user_role'] = 'parent'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('parents_page'))

    return render_template('login/parents.html')


@app.route('/create_parent', methods=['GET', 'POST'])
def create_parent():
    if request.method == 'POST':
        child_id = request.form.get('child_id', '').strip()
        password = request.form.get('password', '').strip()
        if not (child_id and password):
            flash('Child ID and password are required.', 'error')
            return redirect(url_for('create_parent'))
        try:
            child_int = int(child_id)
        except ValueError:
            flash('Child ID must be a number.', 'error')
            return redirect(url_for('create_parent'))

        try:
            with get_db_conn() as (conn, cursor):
                # Verify child exists (using the new student table)
                cursor.execute(f"SELECT ID FROM {TABLE_NAME_STUDENT} WHERE ID=%s", (child_int,))
                student = cursor.fetchone()
                if not student:
                    flash('Student (child) ID not found.', 'error')
                    return redirect(url_for('create_parent'))

                # Insert into parents table
                cursor.execute(f"INSERT INTO {TABLE_NAME_PARENT} (Password, ChildrentID) VALUES (%s, %s) RETURNING ID",
                               (password, child_int))
                new_id = cursor.fetchone()[0] # Get the ID of the new row
                conn.commit()
            
            flash(f'Parent account created (Parent ID: {new_id}). You can sign in with that ID.', 'success')
            return redirect(url_for('parents_page'))
        except psycopg2.errors.UniqueViolation:
            flash('Record already exists (duplicate entry).', 'error')
            return redirect(url_for('create_parent'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_parent'))

    return render_template('sign in/create_parent.html')

# ... (Simplified login/signup to use the more specific routes) ...

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Simplify: Redirect to specific login pages. 
    # The original logic of determining the table name on a generic /login POST is overly complex and error-prone.
    role = request.args.get('role', '').lower()
    
    if request.method == 'POST':
        # Delegate to the specific role's login page (which handles its own POST)
        if role == 'administrator':
            return administrators_page()
        elif role == 'teacher':
            return teachers_page()
        elif role == 'student':
            return students_page()
        elif role == 'parent':
            return parents_page()
        else:
            flash('Invalid role specified.', 'error')
            return redirect(url_for('index'))

    # GET request: Render the appropriate login form
    tmpl = ROLE_TEMPLATES.get(role, 'login.html')
    return render_template(tmpl, role=role)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Simplify: Delegate to specific signup pages
    role = request.args.get('role', '').lower()
    
    if request.method == 'POST':
        if role == 'administrator':
            return create_admin()
        elif role == 'teacher':
            return create_teacher()
        elif role == 'student':
            return create_student()
        elif role == 'parent':
            return create_parent()
        else:
            flash('Invalid role specified.', 'error')
            return redirect(url_for('index'))

    tmpl = SIGNUP_TEMPLATES.get(role, 'signup.html')
    return render_template(tmpl, role=role)

# --- Dashboard and Management Routes (Updated for PostgreSQL and single student table) ---

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('index'))
    
    user_role = session.get('user_role', 'user')
    user_name = session.get('user_name', 'Guest')
    dashboard_map = {
        'administrator': 'admin dashboard/dashboard_admin.html',
        'teacher': 'teacher dashboard/dashboard_teacher.html',
        'student': 'student dashboard/dashboard_student.html',
        'parent': 'parent dashboard/dashboard_parent.html'
    } 
    # Assuming 'admin dashboard/dashboard_admin.html' is a reasonable default 
    # if the role is 'user' or unknown.
    template = dashboard_map.get(user_role, 'admin dashboard/dashboard_admin.html') 
    return render_template(template, name=user_name, role=user_role)

@app.route('/manage_students')
def manage_students():
    q = request.args.get('q', '').strip()
    students = []
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            if q:
                # Note: Using TABLE_NAME_STUDENT_DATA
                cursor.execute(
                    f"SELECT ID, Name, Gender, Class, Grade, Password, Phone FROM {TABLE_NAME_STUDENT_DATA} WHERE Name ILIKE %s ORDER BY ID",
                    (f"%{q}%",) # ILIKE is case-insensitive LIKE in Postgres
                )
            else:
                cursor.execute(
                    f"SELECT ID, Name, Gender, Class, Grade, Password, Phone FROM {TABLE_NAME_STUDENT_DATA} ORDER BY ID"
                )
            students = cursor.fetchall()
    except Exception as e:
        print("manage_students error:", e)
        flash('Database error fetching students.', 'error')
        students = []
    return render_template('admin dashboard/manage_students.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', 'other').strip().lower() or 'other'
        class_ = request.form.get('class', '') or None
        grade = request.form.get('grade', None)
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip() or None

        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('add_student'))

        try:
            with get_db_conn() as (conn, cursor):
                # Insert directly into the single student table (TABLE_NAME_STUDENT_DATA)
                # RETURNING ID is used to get the auto-generated ID in PostgreSQL
                cursor.execute(
                    f"""
                    INSERT INTO {TABLE_NAME_STUDENT_DATA} (Name, Gender, Class, Grade, Password, Phone)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING ID
                    """,
                    (name, gender, class_, grade, password, phone)
                )
                new_id = cursor.fetchone()[0]
                conn.commit()

            flash(f'Student (ID: {new_id}) added successfully.', 'success')
            return redirect(url_for('manage_students'))
        except psycopg2.errors.UniqueViolation:
            flash('A student with this name might already exist.', 'error')
            return redirect(url_for('add_student'))
        except Exception as e:
            print('add_student error:', e)
            flash('Failed to add student: ' + str(e), 'error')
            return redirect(url_for('add_student'))

    return render_template('admin dashboard/add_student.html')

@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    try:
        with get_db_conn() as (conn, cursor):
            # Deleting from student_data is sufficient, as it's now the main table.
            # CASCADE constraints will handle related tables (parents, fees, student_subjects).
            cursor.execute(f"DELETE FROM {TABLE_NAME_STUDENT_DATA} WHERE ID=%s", (id,))
            conn.commit()
            flash('Student deleted successfully.', 'info')
    except Exception as e:
        print('delete_student error:', e)
        flash('Failed to delete student: ' + str(e), 'error')
    return redirect(url_for('manage_students'))

@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            if request.method == 'POST':
                name = request.form.get('name', '').strip()
                gender = request.form.get('gender', 'other')
                class_ = request.form.get('class', '') or None
                grade = request.form.get('grade', None) # Include Grade field in update
                password = request.form.get('password', '')
                phone = request.form.get('phone', '') or None
                
                # Update the single student table
                cursor.execute(
                    f"""
                    UPDATE {TABLE_NAME_STUDENT_DATA} 
                    SET Name=%s, Gender=%s, Class=%s, Grade=%s, Password=%s, Phone=%s 
                    WHERE ID=%s
                    """,
                    (name, gender, class_, grade, password, phone, id)
                )
                conn.commit()
                flash('Student updated successfully.', 'success')
                return redirect(url_for('manage_students'))

            # GET request - fetch student data
            cursor.execute(
                f"SELECT ID, Name, Gender, Class, Grade, Password, Phone FROM {TABLE_NAME_STUDENT_DATA} WHERE ID=%s",
                (id,)
            )
            student = cursor.fetchone()
            
            if not student:
                flash('Student not found.', 'error')
                return redirect(url_for('manage_students'))
            
            return render_template('admin dashboard/edit_student.html', student=student)
    
    except Exception as e:
        print('edit_student error:', e)
        flash('An error occurred during student editing: ' + str(e), 'error')
        return redirect(url_for('manage_students'))

@app.route('/manage_teachers')
def manage_teachers():
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            cursor.execute(f"""
                SELECT t.*, COALESCE(STRING_AGG(s.name, ', ' ORDER BY s.name), '') AS subjects
                FROM {TABLE_NAME_TEACHER} t
                LEFT JOIN subjects s ON t.ID = s.teacher_id
                GROUP BY t.ID
                ORDER BY t.Name
            """)
            teachers = cursor.fetchall()
    except Exception as e:
        print("manage_teachers error:", e)
        flash('Database error fetching teachers.', 'error')
        teachers = []
    return render_template('admin dashboard/manage_teachers.html', teachers=teachers)

@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', 'other').strip().lower() or 'other'
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip() or None

        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('add_teacher'))

        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute(
                    f"INSERT INTO {TABLE_NAME_TEACHER} (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                    (name, password, phone, gender)
                )
                conn.commit()
            flash('Teacher added successfully.', 'success')
            return redirect(url_for('manage_teachers'))
        except psycopg2.errors.UniqueViolation:
            flash('A teacher with this name already exists.', 'error')
            return redirect(url_for('add_teacher'))
        except Exception as e:
            print('add_teacher error:', e)
            flash('Failed to add teacher: ' + str(e), 'error')
            return redirect(url_for('add_teacher'))

    return render_template('admin dashboard/add_teacher.html')

@app.route('/edit_teacher/<int:id>', methods=['GET', 'POST'])
def edit_teacher(id):
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            if request.method == 'POST':
                name = request.form.get('name', '').strip()
                gender = request.form.get('gender', 'other')
                password = request.form.get('password', '')
                phone = request.form.get('phone', '') or None
                
                cursor.execute(
                    f"UPDATE {TABLE_NAME_TEACHER} SET Name=%s, Gender=%s, Password=%s, Phone=%s WHERE ID=%s",
                    (name, gender, password, phone, id)
                )
                conn.commit()
                flash('Teacher updated successfully.', 'success')
                return redirect(url_for('manage_teachers'))

            cursor.execute(
                f"SELECT ID, Name, Gender, Phone, Password FROM {TABLE_NAME_TEACHER} WHERE ID=%s",
                (id,)
            )
            teacher = cursor.fetchone()
            if not teacher:
                flash('Teacher not found.', 'error')
                return redirect(url_for('manage_teachers'))
            return render_template('admin dashboard/edit_teacher.html', teacher=teacher)
    except Exception as e:
        print('edit_teacher error:', e)
        flash('An error occurred.', 'error')
        return redirect(url_for('manage_teachers'))

@app.route('/delete_teacher/<int:id>', methods=['GET','POST'])
def delete_teacher(id):
    try:
        with get_db_conn() as (conn, cursor):
            cursor.execute(f"DELETE FROM {TABLE_NAME_TEACHER} WHERE ID=%s", (id,))
            conn.commit()
            flash('Teacher deleted successfully.', 'info')
    except Exception as e:
        print('delete_teacher error:', e)
        flash('Failed to delete teacher.', 'error')
    return redirect(url_for('manage_teachers'))

@app.route('/manage_schedule')
def manage_schedule():
    schedules_table = []
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            # PostgreSQL ORDER BY FIELD equivalent using CASE statements is too verbose.
            # Using a simplified ORDER BY day, time_start.
            cursor.execute(f"""
                SELECT
                    s.schedule_id,
                    s.ID AS ID,
                    s.Name AS Name,
                    s.Terms AS terms,
                    s.Subject AS subject,
                    s.Day AS day,
                    s.Time_start AS time_start,
                    s.Time_end AS time_end,
                    t.ID AS teacher_id,
                    t.Name AS teacher_name
                FROM {TABLE_NAME_SCHEDULE} s
                LEFT JOIN {TABLE_NAME_TEACHER} t ON s.ID = t.ID
                ORDER BY 
                    CASE s.Day
                        WHEN 'Monday' THEN 1
                        WHEN 'Tuesday' THEN 2
                        WHEN 'Wednesday' THEN 3
                        WHEN 'Thursday' THEN 4
                        WHEN 'Friday' THEN 5
                        WHEN 'Saturday' THEN 6
                        WHEN 'Sunday' THEN 7
                        ELSE 8
                    END, 
                    s.Time_start
            """)
            schedules_table = cursor.fetchall()
    except Exception as e:
        print("manage_schedule error:", e)
        flash('Database error fetching schedules.', 'error')
        schedules_table = []
    return render_template('admin dashboard/manage_schedule.html', schedules=schedules_table)

@app.route('/add_schedule', methods=['GET','POST'])
def add_schedule():
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        teacher_name = request.form.get('teacher_name','').strip()
        terms = request.form.get('terms','').strip()
        subject = request.form.get('subject','').strip()
        day = request.form.get('day','').strip()
        time_start = request.form.get('time_start','')
        time_end = request.form.get('time_end','')

        if not (teacher_id and subject and day and time_start and time_end):
            flash('All fields are required.', 'error')
            return redirect(url_for('add_schedule'))

        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {TABLE_NAME_SCHEDULE} 
                      (ID, Name, Terms, Subject, Day, Time_start, Time_end)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (int(teacher_id), teacher_name, terms, subject, day, time_start, time_end))
                conn.commit()
            flash('Schedule added successfully.', 'success')
            return redirect(url_for('manage_schedule'))
        except Exception as e:
            print('add_schedule error:', e)
            flash('Failed to add schedule: ' + str(e), 'error')
            return redirect(url_for('add_schedule'))
            
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            cursor.execute(f"SELECT ID, Name FROM {TABLE_NAME_TEACHER} ORDER BY Name")
            teachers = cursor.fetchall()
    except Exception as e:
        print('add_schedule GET error:', e)
        flash('Database error fetching teachers.', 'error')
        teachers = []
        
    return render_template('admin dashboard/add_schedule.html', teachers=teachers)

@app.route('/edit_schedule/<int:id>', methods=['GET','POST'])
def edit_schedule(id):
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        teacher_name = request.form.get('teacher_name','').strip()
        terms = request.form.get('terms','').strip()
        subject = request.form.get('subject','').strip()
        day = request.form.get('day','').strip()
        time_start = request.form.get('time_start','')
        time_end = request.form.get('time_end','')
        try:
            with get_db_conn() as (conn, cursor):
                # The original MySQL code updated WHERE ID=%s with the schedule's ID 
                # but used the teacher_id as the first parameter. This must be fixed.
                # Assuming the primary key is 'schedule_id' as defined in init_db().
                # I'll update the route parameter name to schedule_id for clarity.
                schedule_id_param = id # Temporarily keep 'id' for the route

                cursor.execute(f"""
                    UPDATE {TABLE_NAME_SCHEDULE}
                    SET ID=%s, Name=%s, Terms=%s, Subject=%s, 
                        Day=%s, Time_start=%s, Time_end=%s
                    WHERE schedule_id=%s
                """, (int(teacher_id), teacher_name, terms, subject, day, time_start, time_end, schedule_id_param))
                conn.commit()
            flash('Schedule updated successfully.', 'success')
            return redirect(url_for('manage_schedule'))
        except Exception as e:
            print('edit_schedule POST error:', e)
            flash('Failed to update schedule: '+str(e), 'error')
            return redirect(url_for('edit_schedule', id=id))

    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            # Fetch schedule using schedule_id, not teacher ID (ID is the FK to Teacher)
            schedule_id_param = id
            cursor.execute(f"SELECT * FROM {TABLE_NAME_SCHEDULE} WHERE schedule_id=%s", (schedule_id_param,))
            schedule = cursor.fetchone()
            
            cursor.execute(f"SELECT ID, Name FROM {TABLE_NAME_TEACHER} ORDER BY Name")
            teachers = cursor.fetchall()
            
            if not schedule:
                flash('Schedule not found.', 'error')
                return redirect(url_for('manage_schedule'))
    except Exception as e:
        print('edit_schedule GET error:', e)
        flash('An error occurred.', 'error')
        return redirect(url_for('manage_schedule'))

    return render_template('admin dashboard/edit_schedule.html', schedule=schedule, teachers=teachers)

@app.route('/delete_schedule/<int:id>', methods=['POST'])
def delete_schedule(id):
    try:
        with get_db_conn() as (conn, cursor):
            # Assuming 'id' in the route is schedule_id
            cursor.execute(f"DELETE FROM {TABLE_NAME_SCHEDULE} WHERE schedule_id = %s", (id,))
            conn.commit()
            flash('Schedule deleted.', 'info')
    except Exception as e:
        print('delete_schedule error:', e)
        flash('Failed to delete schedule: ' + str(e), 'error')
    return redirect(url_for('manage_schedule'))

@app.route('/manage_subject')
def manage_subject():
    subjects = []
    teachers = []
    all_students = []
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            cursor.execute(f"""
                SELECT s.subject_id, s.name, t.Name AS teacher_name,
                       COUNT(ss.student_id) AS student_count
                FROM subjects s
                LEFT JOIN {TABLE_NAME_TEACHER} t ON s.teacher_id = t.ID
                LEFT JOIN student_subjects ss ON s.subject_id = ss.subject_id
                GROUP BY s.subject_id, s.name, t.Name
                ORDER BY s.subject_id
            """)
            subjects = cursor.fetchall()
            
            # Get enrolled students for each subject
            for subject in subjects:
                cursor.execute(f"""
                    SELECT s.ID, s.Name
                    FROM {TABLE_NAME_STUDENT_DATA} s
                    INNER JOIN student_subjects ss ON s.ID = ss.student_id
                    WHERE ss.subject_id = %s
                    ORDER BY s.Name
                """, (subject['subject_id'],))
                subject['enrolled_students'] = cursor.fetchall()
            
            cursor.execute(f"SELECT ID, Name FROM {TABLE_NAME_TEACHER} ORDER BY Name")
            teachers = cursor.fetchall()
            
            cursor.execute(f"SELECT ID, Name FROM {TABLE_NAME_STUDENT_DATA} ORDER BY Name")
            all_students = cursor.fetchall()
    
    except Exception as e:
        print("manage_subject error:", e)
        flash('Database error fetching subjects/students/teachers.', 'error')
        
    return render_template('admin dashboard/manage_subject.html', 
                         subjects=subjects, 
                         teachers=teachers,
                         all_students=all_students)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form.get('name', '').strip()
    teacher_id = request.form.get('teacher_id') or None
    if not name:
        flash('Subject name is required.', 'error')
        return redirect(url_for('manage_subject'))
        
    try:
        with get_db_conn() as (conn, cursor):
            cursor.execute("INSERT INTO subjects (name, teacher_id) VALUES (%s, %s)", (name, teacher_id if teacher_id else None))
            conn.commit()
        flash('Subject added.', 'success')
    except psycopg2.errors.UniqueViolation:
        flash('A subject with this name already exists.', 'error')
    except Exception as e:
        print("add_subject error:", e)
        flash('Failed to add subject: ' + str(e), 'error')
        
    return redirect(url_for('manage_subject'))

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            if request.method == 'POST':
                name = request.form.get('name', '').strip()
                teacher_id = request.form.get('teacher_id') or None
                cursor.execute("UPDATE subjects SET name=%s, teacher_id=%s WHERE subject_id=%s", (name, teacher_id if teacher_id else None, subject_id))
                conn.commit()
                flash('Subject updated.', 'success')
                return redirect(url_for('manage_subject'))
            
            cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
            subject = cursor.fetchone()
            cursor.execute(f"SELECT ID, Name FROM {TABLE_NAME_TEACHER} ORDER BY Name")
            teachers = cursor.fetchall()
    
    except Exception as e:
        print("edit_subject error:", e)
        flash('Database error during subject edit.', 'error')
        return redirect(url_for('manage_subject'))

    return render_template('admin dashboard/edit_subject.html', subject=subject, teachers=teachers)

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    try:
        with get_db_conn() as (conn, cursor):
            cursor.execute("DELETE FROM subjects WHERE subject_id=%s", (subject_id,))
            conn.commit()
        flash('Subject deleted.', 'info')
    except Exception as e:
        print("delete_subject error:", e)
        flash('Failed to delete subject: ' + str(e), 'error')
        
    return redirect(url_for('manage_subject'))

@app.route('/fee_control')
def fee_control():
    q = request.args.get('q', '').strip()
    student = None
    student_fees = None
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            if q:
                # Try to search by ID first if q is numeric
                search_id = None
                try:
                    search_id = int(q)
                except ValueError:
                    pass
                
                if search_id:
                    # Search by ID (numeric) - Only students enrolled in subjects
                    cursor.execute(f"""
                        SELECT DISTINCT s.ID, s.Name, s.Gender, s.Class, s.Phone
                        FROM {TABLE_NAME_STUDENT_DATA} s
                        INNER JOIN student_subjects ss ON s.ID = ss.student_id
                        WHERE s.ID = %s
                        LIMIT 1
                    """, (search_id,))
                else:
                    # Search by name - Only students enrolled in subjects
                    cursor.execute(f"""
                        SELECT DISTINCT s.ID, s.Name, s.Gender, s.Class, s.Phone
                        FROM {TABLE_NAME_STUDENT_DATA} s
                        INNER JOIN student_subjects ss ON s.ID = ss.student_id
                        WHERE s.Name ILIKE %s
                        ORDER BY s.ID
                        LIMIT 1
                    """, (f"%{q}%",))
                
                student = cursor.fetchone()
                
                if student:
                    student_id = student['id'] # psycopg2 RealDictCursor uses lowercase keys
                    # Get enrolled subjects and their fees for this student
                    cursor.execute(f"""
                        SELECT 
                            COALESCE(f.fee_id, NULL) AS fee_id,
                            ss.student_id,
                            ss.subject_id,
                            COALESCE(f.amount, 65.00) AS amount, 
                            COALESCE(f.paid, 0.00) AS paid,
                            COALESCE(f.status, 'pending') AS status,
                            f.due_date,
                            sub.name AS subject_name,
                            t.Name AS teacher_name
                        FROM student_subjects ss
                        LEFT JOIN subjects sub ON ss.subject_id = sub.subject_id
                        LEFT JOIN {TABLE_NAME_TEACHER} t ON sub.teacher_id = t.ID
                        LEFT JOIN fees f ON f.student_id = ss.student_id AND f.subject_id = ss.subject_id
                        WHERE ss.student_id = %s
                        ORDER BY sub.name
                    """, (student_id,))
                    student_fees = cursor.fetchall()
            
            # Convert dictionary keys back to original case for template
            if student:
                student = {k.capitalize() if k not in ('class', 'phone') else k: v for k, v in student.items()}
                student['ID'] = student['Id'] # Ensure ID is uppercase
                del student['Id'] 
            
            if student_fees:
                 student_fees = [{k: v for k, v in fee.items()} for fee in student_fees]

    except Exception as e:
        print("fee_control error:", e)
        flash('Database error during fee control.', 'error')
        student = None
        student_fees = None
    
    return render_template('admin dashboard/fee_management.html', 
                         student=student, 
                         student_fees=student_fees,
                         search_query=q)

@app.route('/add_fee', methods=['POST'])
def add_fee():
    student_id = request.form.get('student_id')
    subject_id = request.form.get('subject_id')
    amount = request.form.get('amount', 0)
    due_date = request.form.get('due_date')
    
    try:
        amount_float = float(amount) if amount else 0.00
    except ValueError:
        flash('Invalid amount entered.', 'error')
        return redirect(url_for('fee_control', q=student_id))
    
    try:
        with get_db_conn() as (conn, cursor):
            # PostgreSQL equivalent of ON DUPLICATE KEY UPDATE using ON CONFLICT
            cursor.execute("""
                INSERT INTO fees (student_id, subject_id, amount, due_date, status)
                VALUES (%s, %s, %s, %s, 'pending')
                ON CONFLICT (student_id, subject_id) DO UPDATE SET
                    amount = EXCLUDED.amount,
                    due_date = EXCLUDED.due_date,
                    status = 'pending'
            """, (int(student_id), int(subject_id), amount_float, due_date or None))
            conn.commit()
            flash('Fee added/updated successfully.', 'success')
    except Exception as e:
        print("add_fee error:", e)
        flash('Failed to add fee: ' + str(e), 'error')
    
    return redirect(url_for('fee_control', q=student_id))

@app.route('/pay_fee/<int:fee_id>', methods=['POST'])
def pay_fee(fee_id):
    amount_paid = request.form.get('amount_paid', 0)
    student_id = None
    
    try:
        amount_paid_float = float(amount_paid)
    except ValueError:
        flash('Invalid payment amount entered.', 'error')
        # Try to find student ID to redirect
        try:
            with get_db_conn() as (conn, cursor):
                cursor.execute("SELECT student_id FROM fees WHERE fee_id=%s", (fee_id,))
                row = cursor.fetchone()
                if row: student_id = row[0]
        except: pass
        return redirect(url_for('fee_control', q=student_id or ''))

    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            cursor.execute("SELECT student_id, amount, paid FROM fees WHERE fee_id=%s", (fee_id,))
            fee = cursor.fetchone()
            
            if not fee:
                flash('Fee not found.', 'error')
                return redirect(url_for('fee_control'))
            
            student_id = fee['student_id'] # Get student_id for redirect
            
            new_paid = float(fee['paid']) + amount_paid_float
            new_status = 'paid' if new_paid >= float(fee['amount']) else 'partial'
            
            cursor.execute("""
                UPDATE fees SET paid=%s, status=%s WHERE fee_id=%s
            """, (new_paid, new_status, fee_id))
            conn.commit()
            flash('Payment recorded successfully.', 'success')
    except Exception as e:
        print("pay_fee error:", e)
        flash('Failed to record payment: ' + str(e), 'error')
    
    return redirect(url_for('fee_control', q=student_id or ''))

@app.route('/delete_fee/<int:fee_id>', methods=['POST'])
def delete_fee(fee_id):
    student_id = None
    try:
        with get_db_conn(dict_cursor=True) as (conn, cursor):
            cursor.execute("SELECT student_id FROM fees WHERE fee_id=%s", (fee_id,))
            fee = cursor.fetchone()
            if fee:
                student_id = fee['student_id']
            
            cursor.execute("DELETE FROM fees WHERE fee_id=%s", (fee_id,))
            conn.commit()
            flash('Fee deleted.', 'info')
    except Exception as e:
        print("delete_fee error:", e)
        flash('Failed to delete fee: ' + str(e), 'error')
    
    return redirect(url_for('fee_control', q=student_id or ''))


@app.route('/enroll_student', methods=['POST'])
def enroll_student():
    subject_id = request.form.get('subject_id')
    student_id = request.form.get('student_id')
    
    if not (subject_id and student_id):
        flash('Subject and student are required.', 'error')
        return redirect(url_for('manage_subject'))
    
    try:
        with get_db_conn() as (conn, cursor):
            cursor.execute("""
                INSERT INTO student_subjects (student_id, subject_id)
                VALUES (%s, %s)
            """, (int(student_id), int(subject_id)))
            conn.commit()
        flash('Student enrolled successfully.', 'success')
    except psycopg2.errors.UniqueViolation:
        flash('Student already enrolled in this subject.', 'warning')
    except Exception as e:
        print('enroll_student error:', e)
        flash('Failed to enroll student: ' + str(e), 'error')
        
    return redirect(url_for('manage_subject'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print("Failed to initialize database:", e)
        raise

    # When running on Render, the port is set by the environment
    port = int(os.environ.get('PORT', 5000))
    # We must set debug=False when not running locally in production environment
    app.run(host='0.0.0.0', port=port, debug=True)
