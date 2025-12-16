from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import psycopg2 
from psycopg2 import extras
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)
# Use a strong secret key from environment variable for production
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# --- PostgreSQL Connection Setup ---
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

# Define table names (consistent with init_db.py - all lowercase)
TABLE_NAME_ADMIN = "administrators"
TABLE_NAME_STUDENT = "students"
TABLE_NAME_TEACHER = "teachers"
TABLE_NAME_PARENT = "parents"
TABLE_NAME_STUDENT_DATA = "student_data"
TABLE_NAME_SCHEDULE = "schedules_table"
TABLE_NAME_SUBJECT = "subjects"
TABLE_NAME_FEES = "fees"
TABLE_NAME_STUDENT_SUBJECTS = "student_subjects"

def get_db_conn(dict_cursor=False):
    """
    Establishes a connection to the PostgreSQL database.
    If dict_cursor is True, returns a DictCursor for easier column access.
    """
    conn = psycopg2.connect(**DB_CONN_DETAILS)
    cursor = conn.cursor(cursor_factory=extras.DictCursor) if dict_cursor else conn.cursor()
    return conn, cursor

# --- LOGIN UTILITY FUNCTION ---
def handle_login(identifier, password, role, table):
    """Generic function to handle login for any role."""
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        id_column = 'name' 
        if table == TABLE_NAME_STUDENT:
            id_column = 'name' # Students log in by name/username
        elif table == TABLE_NAME_PARENT:
            id_column = 'student_id' # Parents log in by child's student_id
        
        # Check login credentials
        cursor.execute(f"SELECT id, name, password, student_id FROM {table} WHERE {id_column}=%s", (identifier,))
        user = cursor.fetchone()
        
        if user and user['password'] == password:
            session['logged_in'] = True
            session['role'] = role
            # Use 'name' from the DB if available, otherwise use the identifier provided
            session['name'] = user['name'] if 'name' in user and user['name'] else identifier 
            session['user_id'] = user['id']
            if role == 'parent' and user.get('student_id'):
                session['student_id'] = user['student_id']

            flash(f'Logged in as {role.capitalize()}.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials or account not found.', 'error')
            # Render the specific login page again (e.g., 'administrators.html')
            return render_template(f'{table.rstrip("s")}.html') 
    except Exception as e:
        print(f'{role} login error:', e)
        flash('An error occurred during login. Please try again.', 'error')
        return render_template(f'{table.rstrip("s")}.html')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass


# --- AUTHENTICATION ROUTES (SEPARATE TO MATCH HTML FORMS) ---

@app.route('/', methods=['GET'])
def index():
    """Renders the main role selection page."""
    return render_template('index.html') 


@app.route('/administrators_page', methods=['GET', 'POST'])
def administrators_page():
    """Handles Administrator Login."""
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        return handle_login(name, password, 'admin', TABLE_NAME_ADMIN)
    return render_template('administrators.html')


@app.route('/teachers_page', methods=['GET', 'POST'])
def teachers_page():
    """Handles Teacher Login."""
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        return handle_login(name, password, 'teacher', TABLE_NAME_TEACHER)
    return render_template('teachers.html')


@app.route('/students_page', methods=['GET', 'POST'])
def students_page():
    """Handles Student Login."""
    if request.method == 'POST':
        name = request.form.get('name') 
        password = request.form.get('password')
        return handle_login(name, password, 'student', TABLE_NAME_STUDENT)
    return render_template('students.html')


@app.route('/parents_page', methods=['GET', 'POST'])
def parents_page():
    """Handles Parent Login (by student ID)."""
    if request.method == 'POST':
        # Parent form uses 'name' for the Child Student ID
        student_id = request.form.get('name') 
        password = request.form.get('password')
        return handle_login(student_id, password, 'parent', TABLE_NAME_PARENT)
    return render_template('parents.html')

# --- USER MANAGEMENT ROUTES ---

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()
            cursor.execute(f"INSERT INTO {TABLE_NAME_ADMIN} (name, password) VALUES (%s, %s)", (name, password))
            conn.commit()
            flash('Admin account created successfully.', 'success')
            return redirect(url_for('administrators_page'))
        except psycopg2.errors.UniqueViolation:
            flash('Admin name already exists.', 'error')
            return redirect(url_for('create_admin'))
        except Exception as e:
            conn.rollback()
            print('create_admin error:', e)
            flash('Failed to create admin: ' + str(e), 'error')
            return redirect(url_for('create_admin'))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    return render_template('create_admin.html')


# --- DASHBOARD & UTILITY ROUTES ---

def login_required(f):
    """Decorator to check if user is logged in."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """Decorator to check if user has one of the required roles."""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied. Insufficient permissions.', 'warning')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    user_name = session.get('name')
    
    if role == 'admin':
        return render_template('admin dashboard/dashboard.html', user_name=user_name, role=role)
    elif role == 'teacher':
        return render_template('teacher dashboard/dashboard.html', user_name=user_name, role=role, subjects=[], schedule=[])
    elif role == 'student':
        # Placeholder for student data fetch logic
        student_data = {} 
        return render_template('student dashboard/dashboard.html', user_name=user_name, role=role, student_data=student_data)
    elif role == 'parent':
        # Placeholder for parent dashboard (e.g., viewing child's data)
        return render_template('parent dashboard/dashboard.html', user_name=user_name, role=role)

    else:
        flash('Unknown role.', 'error')
        return redirect(url_for('index'))

# --- CRUD for Students, Teachers, Subjects, Schedules, Fees ---
# NOTE: The rest of the routes (manage_students, add_student, manage_teachers, etc.)
# are correctly set up for PostgreSQL in the full code, so they are omitted for brevity 
# but should be included in your final app.py file. 
# Make sure to copy the full app.py from the previous correct step if you need those functions.


@app.route('/manage_students')
@role_required(['admin'])
def manage_students():
    # Example student management logic using PostgreSQL
    conn = None
    cursor = None
    students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"""
            SELECT s.id, s.name, sd.gender, sd.class, sd.grade, sd.phone
            FROM {TABLE_NAME_STUDENT} s
            LEFT JOIN {TABLE_NAME_STUDENT_DATA} sd ON s.id = sd.id
            ORDER BY s.id
        """)
        students = cursor.fetchall()
    except Exception as e:
        print('manage_students error:', e)
        flash('Error retrieving students.', 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/manage_students.html', students=students)
# ... other CRUD functions go here ...


# --- LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    try:
        # Import and run init_db to ensure database structure is ready
        import init_db
        init_db.init_db()
        print("Database structure verified.")
    except Exception as e:
        print(f"Error during initial database setup: {e}")
        # Application will still run, but database connections might fail
    
    app.run(debug=True)
