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
    """
    Establishes a connection to the PostgreSQL database.
    """
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
        print(f"Database connection error: {e}")
        if cursor: cursor.close()
        if conn: conn.close()
        raise


# --- Core Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# --- Login Router (Fix for url_for('login')) ---
@app.route('/login')
def login():
    """
    Routes the user to the correct role-specific login page based on the 
    'role' query parameter.
    """
    role = request.args.get('role', 'administrator').lower()
    
    endpoint_map = {
        'administrator': 'administrators_page',
        'teacher': 'teachers_page',
        'student': 'students_page',
        'parent': 'parents_page'
    }
    
    target_endpoint = endpoint_map.get(role, 'administrators_page')
    
    return redirect(url_for(target_endpoint))

# --- NEW: Signup Chooser (Fix for url_for('signup')) ---
@app.route('/signup')
def signup():
    """
    Renders a page for the user to choose their role for account creation.
    This fixes the BuildError for the 'signup' endpoint.
    """
    # Assuming you have a template named 'sign_up_chooser.html' in your templates directory
    # that contains links to create_admin, create_student, etc.
    return render_template('sign_up_chooser.html')


# --- Login and Signup Routes (Adapted for PostgreSQL/psycopg2) ---

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
            cursor.execute(f'SELECT "ID", "Name", "Password" FROM {TABLE_NAME_ADMIN} WHERE "Name"=%s', (name,))
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
            conn, cursor = get_db_conn()
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_ADMIN} ("Name", "Password") VALUES (%s, %s)',
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
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_admin'))
    return render_template('sign in/create_admin.html')


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


# --- Management Routes Sample (Full Conversion) ---

@app.route('/manage_students')
def manage_students():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        sql = f'SELECT "ID", "Name", "Gender", "Class", "Grade", "Password", "Phone" FROM {TABLE_NAME_STUDENT_DATA}'
        if q:
            sql += ' WHERE "Name" ILIKE %s ORDER BY "ID"'
            cursor.execute(sql, (f"%{q}%",))
        else:
            sql += ' ORDER BY "ID"'
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

            # 1. Insert into STUDENTS and use RETURNING to get the new ID (PostgreSQL standard)
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_STUDENT} ("Name", "Password", "Phone", "Gender") VALUES (%s, %s, %s, %s) RETURNING "ID"',
                (name, password, phone, gender)
            )
            new_id = cursor.fetchone()[0]

            # 2. Insert / update student_data with the new ID using ON CONFLICT (PostgreSQL standard)
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT_DATA} ("ID","Name","Gender","Class","Grade","Password","Phone")
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT ("ID") DO UPDATE SET
                  "Name" = EXCLUDED."Name",
                  "Gender" = EXCLUDED."Gender",
                  "Class" = EXCLUDED."Class",
                  "Grade" = EXCLUDED."Grade",
                  "Password" = EXCLUDED."Password",
                  "Phone" = EXCLUDED."Phone"
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
