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


def get_db_conn(dict_cursor=False):
    """Establishes a connection to the PostgreSQL database. Raises error on failure."""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONN_DETAILS)
        if dict_cursor:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        # CRITICAL: This allows the error to be caught by Flask and displayed/logged correctly.
        print(f"Database connection error: {e}")
        raise 


# --- Core Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    """Routes the user to the correct role-specific login page."""
    role = request.args.get('role', 'administrator').lower()
    
    endpoint_map = {
        'administrator': 'administrators_page',
        'teacher': 'teachers_page',
        'student': 'students_page',
        'parent': 'parents_page'
    }
    
    target_endpoint = endpoint_map.get(role, 'administrators_page')
    
    return redirect(url_for(target_endpoint))

@app.route('/signup')
def signup():
    """Renders a page for the user to choose their role for account creation."""
    return render_template('sign_up_chooser.html')


# --- ADMINISTRATOR ROUTES (Login/Creation) ---

@app.route('/administrators', methods=['GET', 'POST'])
def administrators_page():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('administrators_page'))
        try:
            conn, cursor = get_db_conn()
            cursor.execute(f'SELECT id, name, password FROM {TABLE_NAME_ADMIN} WHERE name=%s', (name,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row or password != row[2]:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('administrators_page'))
            session['user_id'] = row[0]
            session['user_name'] = row[1]
            session['user_role'] = 'administrator'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Login error: ' + str(e), 'error')
            return redirect(url_for('administrators_page'))
    # Using 'login/administrators.html' is standard for a clean project structure
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
            conn, cursor = get_db_conn()
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_ADMIN} (name, password) VALUES (%s, %s)',
                (name, password)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Administrator account created. You can now sign in.', 'success')
            return redirect(url_for('administrators_page'))
        except psycopg2.errors.UniqueViolation:
            flash('An account with that name already exists.', 'error')
            return redirect(url_for('create_admin'))
        except Exception as e:
            flash('Creation error: ' + str(e), 'error')
            return redirect(url_for('create_admin'))
    # Using 'sign in/create_admin.html' based on your provided structure
    return render_template('sign in/create_admin.html')


# --- TEACHER ROUTES (Login/Creation) ---

@app.route('/teachers', methods=['GET', 'POST'])
def teachers_page():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('teachers_page'))
        try:
            conn, cursor = get_db_conn()
            cursor.execute(f'SELECT id, name, password FROM {TABLE_NAME_TEACHER} WHERE name=%s', (name,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row or password != row[2]:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('teachers_page'))
            session['user_id'] = row[0]
            session['user_name'] = row[1]
            session['user_role'] = 'teacher'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Login error: ' + str(e), 'error')
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
            conn, cursor = get_db_conn()
            # Uses lowercase columns: name, password, phone, gender
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_TEACHER} (name, password, phone, gender) VALUES (%s, %s, %s, %s)',
                (name, password, phone, gender)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Teacher account created. You can now sign in.', 'success')
            return redirect(url_for('teachers_page'))
        except psycopg2.errors.UniqueViolation:
            flash('An account with that name already exists.', 'error')
            return redirect(url_for('create_teacher'))
        except Exception as e:
            flash('Creation error: ' + str(e), 'error')
            return redirect(url_for('create_teacher'))
    return render_template('sign in/create_teacher.html')


# --- STUDENT ROUTES (Login/Creation) ---

@app.route('/students', methods=['GET', 'POST'])
def students_page():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('students_page'))
        try:
            conn, cursor = get_db_conn()
            cursor.execute(f'SELECT id, name, password FROM {TABLE_NAME_STUDENT} WHERE name=%s', (name,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row or password != row[2]:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('students_page'))
            session['user_id'] = row[0]
            session['user_name'] = row[1]
            session['user_role'] = 'student'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Login error: ' + str(e), 'error')
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
            conn, cursor = get_db_conn()
            
            # 1. Insert into STUDENTS and get the new ID
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_STUDENT} (name, password, phone, gender) VALUES (%s, %s, %s, %s) RETURNING id',
                (name, password, phone, gender)
            )
            new_id = cursor.fetchone()[0] 
            
            # 2. Insert into STUDENT_DATA (maintaining consistency)
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_STUDENT_DATA} (id, name, gender, password, phone) VALUES (%s, %s, %s, %s, %s)',
                (new_id, name, gender, password, phone)
            )

            conn.commit()
            cursor.close()
            conn.close()
            flash('Student account created. You can now sign in.', 'success')
            return redirect(url_for('students_page'))
        except psycopg2.errors.UniqueViolation:
            flash('An account with that name already exists.', 'error')
            return redirect(url_for('create_student'))
        except Exception as e:
            flash('Creation error: ' + str(e), 'error')
            return redirect(url_for('create_student'))
    return render_template('sign in/create_student.html')


# --- PARENT ROUTES (Login/Creation) ---

@app.route('/parents', methods=['GET', 'POST'])
def parents_page():
    if request.method == 'POST':
        pid = request.form.get('name', '').strip()
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
            conn, cursor = get_db_conn()
            cursor.execute(f'SELECT id, password FROM {TABLE_NAME_PARENT} WHERE id=%s', (parent_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row or password != row[1]:
                flash('Invalid Parent ID or password.', 'error')
                return redirect(url_for('parents_page'))

            session['user_id'] = row[0]
            session['user_name'] = f"Parent#{row[0]}"
            session['user_role'] = 'parent'
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Login error: ' + str(e), 'error')
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
            conn, cursor = get_db_conn()
            # Verify child exists (lowercase 'id')
            cursor.execute(f'SELECT id FROM {TABLE_NAME_STUDENT} WHERE id=%s', (child_int,))
            student = cursor.fetchone()
            if not student:
                flash('Student (child) ID not found.', 'error')
                cursor.close(); conn.close()
                return redirect(url_for('create_parent'))

            # Insert new parent record (lowercase 'password', 'childrentid')
            cursor.execute(f'INSERT INTO {TABLE_NAME_PARENT} (password, childrentid) VALUES (%s, %s) RETURNING id',
                           (password, child_int))
            new_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            flash(f'Parent account created (Parent ID: {new_id}). You can sign in with that ID.', 'success')
            return redirect(url_for('parents_page'))
        except psycopg2.errors.UniqueViolation:
            flash('A parent is already registered for this child, or the ID is duplicated.', 'error')
            return redirect(url_for('create_parent'))
        except Exception as e:
            flash('Creation error: ' + str(e), 'error')
            return redirect(url_for('create_parent'))

    return render_template('sign in/create_parent.html')


# --- DASHBOARD & MANAGEMENT ROUTES ---

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
    template = dashboard_map.get(user_role, 'admin dashboard/dashboard_admin.html')
    return render_template(template, name=user_name, role=user_role)


# --- NEW TEACHER MANAGEMENT ROUTES (Fix for BuildError) ---

@app.route('/manage_teachers')
def manage_teachers():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    teachers = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        # Using lowercase column names: id, name, gender, phone
        sql = f'SELECT id, name, gender, phone FROM {TABLE_NAME_TEACHER}'
        if q:
            sql += ' WHERE name ILIKE %s ORDER BY id'
            cursor.execute(sql, (f"%{q}%",))
        else:
            sql += ' ORDER BY id'
            cursor.execute(sql)
        teachers = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("manage_teachers error:", e)
        flash('Failed to load teachers: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    # NOTE: You must have a template named 'admin dashboard/manage_teachers.html'
    return render_template('admin dashboard/manage_teachers.html', teachers=teachers)


@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip() or None
        gender = request.form.get('gender', 'other').strip().lower() or 'other'
        
        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('add_teacher'))

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()

            cursor.execute(
                f'INSERT INTO {TABLE_NAME_TEACHER} (name, password, phone, gender) VALUES (%s, %s, %s, %s)',
                (name, password, phone, gender)
            )
            conn.commit()

            flash('Teacher added successfully.', 'success')
            return redirect(url_for('manage_teachers'))
        except psycopg2.errors.UniqueViolation:
            flash('Teacher name already exists.', 'error')
            return redirect(url_for('add_teacher'))
        except Exception as e:
            print('add_teacher error:', e)
            flash('Failed to add teacher: ' + str(e), 'error')
            return redirect(url_for('add_teacher'))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    # NOTE: You must have a template named 'admin dashboard/add_teacher.html'
    return render_template('admin dashboard/add_teacher.html')

# --- EXISTING STUDENT MANAGEMENT ROUTES ---

@app.route('/manage_students')
def manage_students():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        # Using lowercase column names
        sql = f'SELECT id, name, gender, class, grade, password, phone FROM {TABLE_NAME_STUDENT_DATA}'
        if q:
            sql += ' WHERE name ILIKE %s ORDER BY id'
            cursor.execute(sql, (f"%{q}%",))
        else:
            sql += ' ORDER BY id'
            cursor.execute(sql)
        students = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("manage_students error:", e)
        flash('Failed to load students: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
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

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()

            # 1. Insert into STUDENTS and use RETURNING to get the new ID (lowercase 'id')
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_STUDENT} (name, password, phone, gender) VALUES (%s, %s, %s, %s) RETURNING id',
                (name, password, phone, gender)
            )
            new_id = cursor.fetchone()[0]

            # 2. Insert / update student_data with the new ID using ON CONFLICT 
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT_DATA} (id, name, gender, class, grade, password, phone)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  gender = EXCLUDED.gender,
                  class = EXCLUDED.class,
                  grade = EXCLUDED.grade,
                  password = EXCLUDED.password,
                  phone = EXCLUDED.phone
                """,
                (new_id, name, gender, class_, grade, password, phone)
            )
            conn.commit()

            flash('Student added successfully.', 'success')
            return redirect(url_for('manage_students'))
        except psycopg2.errors.UniqueViolation:
            flash('Student name already exists.', 'error')
            return redirect(url_for('add_student'))
        except Exception as e:
            print('add_student error:', e)
            flash('Failed to add student: ' + str(e), 'error')
            return redirect(url_for('add_student'))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    return render_template('admin dashboard/add_student.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
