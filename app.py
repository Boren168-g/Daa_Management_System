from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import psycopg2 
from psycopg2 import extras
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)
# Use a strong secret key from environment variable for production
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# --- PostgreSQL Connection Setup (Based on init_db.py) ---
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    # Placeholder URL - PLEASE ENSURE YOUR RENDER ENVIRONMENT VARIABLE IS SET
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

def init_db():
    # Placeholder for database initialization logic. 
    # Since init_db.py exists, we assume it's run separately on deployment.
    pass

def get_db_conn(dict_cursor=False):
    """Establishes a connection to the PostgreSQL database using psycopg2."""
    conn = psycopg2.connect(**DB_CONN_DETAILS)
    if dict_cursor:
        # Use DictCursor for fetching results as dictionaries
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
    else:
        cursor = conn.cursor()
    return conn, cursor

# --- TEMPLATE/ROLE MAPPING (UNCHANGED) ---
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

# --- INDEX ROUTE (UNCHANGED) ---
@app.route('/')
def index():
    return render_template('index.html')
app.add_url_rule('/', endpoint='index', view_func=index)

# --- ADMINISTRATORS LOGIN & SIGNUP (CONVERTED TO POSTGRESQL) ---
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
            # PostgreSQL column names are typically lowercase
            cursor.execute(f"SELECT id, name, password FROM {TABLE_NAME_ADMIN} WHERE name=%s", (name,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
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
            conn, cursor = get_db_conn()
            cursor.execute(
                f"INSERT INTO {TABLE_NAME_ADMIN} (name, password) VALUES (%s, %s)",
                (name, password)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Administrator account created. You can now sign in.', 'success')
            return redirect(url_for('administrators_page'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Record already exists (duplicate name).', 'error')
            return redirect(url_for('create_admin'))
        except Exception as e:
            conn.rollback()
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_admin'))
    return render_template('sign in/create_admin.html')

# --- TEACHERS LOGIN & SIGNUP (CONVERTED TO POSTGRESQL) ---
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
            cursor.execute(f"SELECT id, name, password FROM {TABLE_NAME_TEACHER} WHERE name=%s", (name,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
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
            conn, cursor = get_db_conn()
            cursor.execute(
                f"INSERT INTO {TABLE_NAME_TEACHER} (name, password, phone, gender) VALUES (%s, %s, %s, %s)",
                (name, password, phone, gender)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Teacher account created. You can now sign in.', 'success')
            return redirect(url_for('teachers_page'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Record already exists (duplicate name).', 'error')
            return redirect(url_for('create_teacher'))
        except Exception as e:
            conn.rollback()
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_teacher'))
    return render_template('sign in/create_teacher.html')

# --- STUDENTS LOGIN & SIGNUP (CONVERTED TO POSTGRESQL) ---
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
            cursor.execute(f"SELECT id, name, password FROM {TABLE_NAME_STUDENT} WHERE name=%s", (name,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
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
            conn, cursor = get_db_conn()
            cursor.execute(
                f"INSERT INTO {TABLE_NAME_STUDENT} (name, password, phone, gender) VALUES (%s, %s, %s, %s)",
                (name, password, phone, gender)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Student account created. You can now sign in.', 'success')
            return redirect(url_for('students_page'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Record already exists (duplicate name).', 'error')
            return redirect(url_for('create_student'))
        except Exception as e:
            conn.rollback()
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_student'))
    return render_template('sign in/create_student.html')

# --- PARENTS LOGIN & SIGNUP (CONVERTED TO POSTGRESQL) ---
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
            cursor.execute(f"SELECT id, password FROM {TABLE_NAME_PARENT} WHERE id=%s", (parent_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
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

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()
            # Verify child exists
            cursor.execute(f"SELECT id FROM {TABLE_NAME_STUDENT} WHERE id=%s", (child_int,))
            student = cursor.fetchone()
            if not student:
                flash('Student (child) ID not found.', 'error')
                return redirect(url_for('create_parent'))

            # Use RETURNING to get the ID after insertion (PostgreSQL equivalent of lastrowid)
            cursor.execute(f"INSERT INTO {TABLE_NAME_PARENT} (password, childrentid) VALUES (%s, %s) RETURNING id",
                           (password, child_int))
            new_id = cursor.fetchone()[0]
            conn.commit()
            
            flash(f'Parent account created (Parent ID: {new_id}). You can sign in with that ID.', 'success')
            return redirect(url_for('parents_page'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Record already exists (duplicate child ID).', 'error')
            return redirect(url_for('create_parent'))
        except Exception as e:
            conn.rollback()
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_parent'))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    return render_template('sign in/create_parent.html')

# --- GENERIC LOGIN/SIGNUP (CONVERTED TO POSTGRESQL) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get('role', '').lower()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('login', role=role))
        table_map = {
            'administrator': TABLE_NAME_ADMIN,
            'teacher': TABLE_NAME_TEACHER,
            'student': TABLE_NAME_STUDENT,
            'parent': TABLE_NAME_PARENT
        }
        table = table_map.get(role, None)

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()
            user_id, user_name, db_password = None, None, None
            
            # Simplified login logic based on role
            if table == TABLE_NAME_PARENT:
                try:
                    parent_id = int(name)
                except ValueError:
                    flash('For parent login enter numeric Parent ID.', 'error')
                    return redirect(url_for('login', role=role))
                cursor.execute(f"SELECT id, password FROM {table} WHERE id=%s", (parent_id,))
                prow = cursor.fetchone()
                if prow:
                    user_id = prow[0]; user_name = f"Parent#{user_id}"; db_password = prow[1]
            elif table in [TABLE_NAME_ADMIN, TABLE_NAME_TEACHER, TABLE_NAME_STUDENT]:
                cursor.execute(f"SELECT id, name, password FROM {table} WHERE name=%s", (name,))
                trow = cursor.fetchone()
                if trow:
                    user_id, user_name, db_password = trow
            else:
                # If role is unknown, try checking all tables
                for t in [TABLE_NAME_ADMIN, TABLE_NAME_TEACHER, TABLE_NAME_STUDENT]:
                    cursor.execute(f"SELECT id, name, password FROM {t} WHERE name=%s", (name,))
                    row = cursor.fetchone()
                    if row:
                        user_id, user_name, db_password = row
                        session['user_role'] = t[:-1] # Set role based on table name (e.g., 'administrators' -> 'administrator')
                        break
            
            if user_name is None:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('login', role=role))
                
            if password == db_password:
                session['user_name'] = user_name
                if 'user_role' not in session:
                    session['user_role'] = role # Use the provided role if not already set by the catch-all
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials.', 'error')
                return redirect(url_for('login', role=role))

        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('login', role=role))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    tmpl = ROLE_TEMPLATES.get(role, 'login.html')
    return render_template(tmpl, role=role)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # This function is not fully implemented in the user's MySQL logic, 
    # and redirects to role-specific signups anyway. Keeping the structure.
    role = request.args.get('role', '').lower()
    tmpl = SIGNUP_TEMPLATES.get(role, 'signup.html')
    return render_template(tmpl, role=role)

# --- DASHBOARD (UNCHANGED) ---
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
    # This is the original line that failed and is now fixed by having the manage_subject route:
    return render_template(template, name=user_name, role=user_role)

# --- STUDENT MANAGEMENT (CONVERTED TO POSTGRESQL) ---
@app.route('/manage_students')
def manage_students():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        if q:
            # PostgreSQL column names are lowercase
            cursor.execute(
                f"SELECT id, name, gender, class, grade, password, phone FROM {TABLE_NAME_STUDENT_DATA} WHERE name ILIKE %s ORDER BY id", # ILIKE for case-insensitive search
                (f"%{q}%",)
            )
        else:
            cursor.execute(
                f"SELECT id, name, gender, class, grade, password, phone FROM {TABLE_NAME_STUDENT_DATA} ORDER BY id"
            )
        students = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("manage_students error:", e)
        students = []
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

            # Insert into students table, and use RETURNING to get the new ID
            cursor.execute(
                f"INSERT INTO {TABLE_NAME_STUDENT} (name, password, phone, gender) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, password, phone, gender)
            )
            new_id = cursor.fetchone()[0]

            # Insert / update student_data with same ID using ON CONFLICT (PostgreSQL equivalent of ON DUPLICATE KEY UPDATE)
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
            conn.rollback()
            flash('Student name already exists.', 'error')
            return redirect(url_for('add_student'))
        except Exception as e:
            conn.rollback()
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

@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        # Due to ON DELETE CASCADE constraints, deleting from the main student table should handle student_data
        cursor.execute(f"DELETE FROM {TABLE_NAME_STUDENT} WHERE id=%s", (id,))
        conn.commit()
        flash('Student deleted successfully.', 'info')
    except Exception as e:
        conn.rollback()
        print('delete_student error:', e)
        flash('Failed to delete student: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_students'))

@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            gender = request.form.get('gender', 'other')
            class_ = request.form.get('class', '') or None
            grade = request.form.get('grade', None) # Added grade field
            password = request.form.get('password', '')
            phone = request.form.get('phone', '')
            
            # Update student_data
            cursor.execute(
                f"UPDATE {TABLE_NAME_STUDENT_DATA} SET name=%s, gender=%s, class=%s, grade=%s, password=%s, phone=%s WHERE id=%s",
                (name, gender, class_, grade, password, phone, id)
            )
            # Update main student table (which should be triggered by student_data update or done explicitly)
            cursor.execute(
                f"UPDATE {TABLE_NAME_STUDENT} SET name=%s, gender=%s, password=%s, phone=%s WHERE id=%s",
                (name, gender, password, phone, id)
            )
            
            conn.commit()
            flash('Student updated successfully.', 'success')
            return redirect(url_for('manage_students'))

        # GET request - fetch student data
        cursor.execute(
            f"SELECT id, name, gender, class, grade, password, phone FROM {TABLE_NAME_STUDENT_DATA} WHERE id=%s",
            (id,)
        )
        student = dict(cursor.fetchone())
        
        if not student:
            flash('Student not found.', 'error')
            return redirect(url_for('manage_students'))
        
        return render_template('admin dashboard/edit_student.html', student=student)
    
    except Exception as e:
        print('edit_student error:', e)
        flash('An error occurred.', 'error')
        return redirect(url_for('manage_students'))
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

# --- TEACHER MANAGEMENT (CONVERTED TO POSTGRESQL) ---
@app.route('/manage_teachers')
def manage_teachers():
    conn = None
    cursor = None
    teachers = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"""
            SELECT t.*, STRING_AGG(s.name, ', ') AS subjects -- MySQL GROUP_CONCAT replaced with STRING_AGG
            FROM {TABLE_NAME_TEACHER} t
            LEFT JOIN {TABLE_NAME_SUBJECT} s ON t.id = s.teacher_id
            GROUP BY t.id, t.name, t.password, t.phone, t.gender
            ORDER BY t.name
        """)
        teachers = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print('manage_teachers error:', e)
        teachers = []
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
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

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()
            cursor.execute(
                f"INSERT INTO {TABLE_NAME_TEACHER} (name, password, phone, gender) VALUES (%s, %s, %s, %s)",
                (name, password, phone, gender)
            )
            conn.commit()
            flash('Teacher added successfully.', 'success')
            return redirect(url_for('manage_teachers'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Teacher name already exists.', 'error')
            return redirect(url_for('add_teacher'))
        except Exception as e:
            conn.rollback()
            print('add_teacher error:', e)
            flash('Failed to add teacher: ' + str(e), 'error')
            return redirect(url_for('add_teacher'))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    return render_template('admin dashboard/add_teacher.html')

@app.route('/edit_teacher/<int:id>', methods=['GET', 'POST'])
def edit_teacher(id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            gender = request.form.get('gender', 'other')
            password = request.form.get('password', '')
            phone = request.form.get('phone', '')
            cursor.execute(
                f"UPDATE {TABLE_NAME_TEACHER} SET name=%s, gender=%s, password=%s, phone=%s WHERE id=%s",
                (name, gender, password, phone, id)
            )
            conn.commit()
            flash('Teacher updated successfully.', 'success')
            return redirect(url_for('manage_teachers'))

        cursor.execute(
            f"SELECT id, name, gender, phone, password FROM {TABLE_NAME_TEACHER} WHERE id=%s",
            (id,)
        )
        teacher = dict(cursor.fetchone())
        if not teacher:
            flash('Teacher not found.', 'error')
            return redirect(url_for('manage_teachers'))
        return render_template('admin dashboard/edit_teacher.html', teacher=teacher)
    except Exception as e:
        print('edit_teacher error:', e)
        flash('An error occurred.', 'error')
        return redirect(url_for('manage_teachers'))
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

@app.route('/delete_teacher/<int:id>', methods=['POST'])
def delete_teacher(id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"DELETE FROM {TABLE_NAME_TEACHER} WHERE id=%s", (id,))
        conn.commit()
        flash('Teacher deleted successfully.', 'info')
    except Exception as e:
        conn.rollback()
        print('delete_teacher error:', e)
        flash('Failed to delete teacher.', 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_teachers'))

# --- SCHEDULE MANAGEMENT (CONVERTED TO POSTGRESQL) ---
@app.route('/manage_schedule')
def manage_schedule():
    conn = None
    cursor = None
    schedules_table = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"""
            SELECT
                s.schedule_id,
                s.id AS id,
                s.name AS name,
                s.terms AS terms,
                s.subject AS subject,
                s.day AS day,
                s.time_start AS time_start,
                s.time_end AS time_end,
                t.id AS teacher_id,
                t.name AS teacher_name
            FROM {TABLE_NAME_SCHEDULE} s
            LEFT JOIN {TABLE_NAME_TEACHER} t ON s.id = t.id
            ORDER BY 
                CASE s.day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                    ELSE 8 
                END, 
                s.time_start
        """)
        schedules_table = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("manage_schedule error:", e)
        schedules_table = []
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return render_template('admin dashboard/manage_schedule.html', schedules=schedules_table)

@app.route('/add_schedule', methods=['GET','POST'])
def add_schedule():
    conn = None
    cursor = None
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
            conn, cursor = get_db_conn()
            cursor.execute(f"""
                INSERT INTO {TABLE_NAME_SCHEDULE} 
                  (id, name, terms, subject, day, time_start, time_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (int(teacher_id), teacher_name, terms, subject, day, time_start, time_end))
            conn.commit()
            flash('Schedule added successfully.', 'success')
            return redirect(url_for('manage_schedule'))
        except Exception as e:
            conn.rollback()
            print('add_schedule error:', e)
            flash('Failed to add schedule: ' + str(e), 'error')
            return redirect(url_for('add_schedule'))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY name")
        teachers = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print('add_schedule GET error:', e)
        teachers = []
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return render_template('admin dashboard/add_schedule.html', teachers=teachers)

@app.route('/edit_schedule/<int:id>', methods=['GET','POST'])
def edit_schedule(id):
    conn = None
    cursor = None
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        teacher_name = request.form.get('teacher_name','').strip()
        terms = request.form.get('terms','').strip()
        subject = request.form.get('subject','').strip()
        day = request.form.get('day','').strip()
        time_start = request.form.get('time_start','')
        time_end = request.form.get('time_end','')
        try:
            conn, cursor = get_db_conn()
            cursor.execute(f"""
                UPDATE {TABLE_NAME_SCHEDULE}
                SET id=%s, name=%s, terms=%s, subject=%s, 
                    day=%s, time_start=%s, time_end=%s
                WHERE schedule_id=%s
            """, (int(teacher_id), teacher_name, terms, subject, day, time_start, time_end, id)) # Use schedule_id for WHERE clause
            conn.commit()
            flash('Schedule updated successfully.', 'success')
            return redirect(url_for('manage_schedule'))
        except Exception as e:
            conn.rollback()
            print('edit_schedule POST error:', e)
            flash('Failed to update schedule: '+str(e), 'error')
            return redirect(url_for('edit_schedule', id=id))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"SELECT * FROM {TABLE_NAME_SCHEDULE} WHERE schedule_id=%s", (id,)) # Use schedule_id for lookup
        schedule = dict(cursor.fetchone())
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY name")
        teachers = [dict(row) for row in cursor.fetchall()]
        if not schedule:
            flash('Schedule not found.', 'error')
            return redirect(url_for('manage_schedule'))
    except Exception as e:
        print('edit_schedule GET error:', e)
        flash('An error occurred.', 'error')
        return redirect(url_for('manage_schedule'))
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return render_template('admin dashboard/edit_schedule.html', schedule=schedule, teachers=teachers)

@app.route('/delete_schedule/<int:id>', methods=['POST'])
def delete_schedule(id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"DELETE FROM {TABLE_NAME_SCHEDULE} WHERE schedule_id = %s", (id,)) # Use schedule_id for delete
        conn.commit()
        flash('Schedule deleted.', 'info')
    except Exception as e:
        conn.rollback()
        print('delete_schedule error:', e)
        flash('Failed to delete schedule: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_schedule'))

# --- SUBJECT MANAGEMENT (CONVERTED TO POSTGRESQL - The requested block) ---
@app.route('/manage_subject')
def manage_subject():
    conn = None
    cursor = None
    subjects = []
    teachers = []
    all_students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # 1. Fetch subjects with associated teacher name and student count
        # MySQL GROUP_CONCAT replaced with PostgreSQL STRING_AGG
        cursor.execute(f"""
            SELECT 
                s.subject_id, 
                s.name, 
                t.name AS teacher_name,
                COUNT(ss.student_id) AS student_count
            FROM {TABLE_NAME_SUBJECT} s
            LEFT JOIN {TABLE_NAME_TEACHER} t ON s.teacher_id = t.id
            LEFT JOIN {TABLE_NAME_STUDENT_SUBJECTS} ss ON s.subject_id = ss.subject_id
            GROUP BY s.subject_id, s.name, t.name
            ORDER BY s.subject_id
        """)
        subjects = [dict(row) for row in cursor.fetchall()]
        
        # 2. Get enrolled students for each subject
        for subject in subjects:
            cursor.execute(f"""
                SELECT s.id, s.name
                FROM {TABLE_NAME_STUDENT} s
                INNER JOIN {TABLE_NAME_STUDENT_SUBJECTS} ss ON s.id = ss.student_id
                WHERE ss.subject_id = %s
                ORDER BY s.name
            """, (subject['subject_id'],))
            subject['enrolled_students'] = [dict(row) for row in cursor.fetchall()]
        
        # 3. Fetch all teachers and students for dropdowns
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY name")
        teachers = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_STUDENT} ORDER BY name")
        all_students = [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        print("manage_subject error (PostgreSQL):", e)
        flash('Failed to load subject data.', 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
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
        
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        # Use RETURNING to get the ID after insertion (PostgreSQL equivalent of lastrowid)
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME_SUBJECT} (name, teacher_id) 
            VALUES (%s, %s)
            RETURNING subject_id
        """, (name, teacher_id if teacher_id else None))
        
        conn.commit()
        flash('Subject added.', 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash('Subject name already exists.', 'error')
    except Exception as e:
        conn.rollback()
        print('add_subject error (PostgreSQL):', e)
        flash('Failed to add subject: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_subject'))

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            teacher_id = request.form.get('teacher_id') or None
            
            cursor.execute(f"UPDATE {TABLE_NAME_SUBJECT} SET name=%s, teacher_id=%s WHERE subject_id=%s", 
                           (name, teacher_id if teacher_id else None, subject_id))
            conn.commit()
            flash('Subject updated.', 'success')
            return redirect(url_for('manage_subject'))
            
        # GET request
        cursor.execute(f"SELECT * FROM {TABLE_NAME_SUBJECT} WHERE subject_id=%s", (subject_id,))
        subject = dict(cursor.fetchone())
        
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY name")
        teachers = [dict(row) for row in cursor.fetchall()]
        
        if not subject:
            flash('Subject not found.', 'error')
            return redirect(url_for('manage_subject'))
            
        return render_template('admin dashboard/edit_subject.html', subject=subject, teachers=teachers)
    
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash('Subject name already exists.', 'error')
        return redirect(url_for('edit_subject', subject_id=subject_id))
    except Exception as e:
        conn.rollback()
        print('edit_subject error (PostgreSQL):', e)
        flash('An error occurred during subject operation: ' + str(e), 'error')
        return redirect(url_for('manage_subject'))
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"DELETE FROM {TABLE_NAME_SUBJECT} WHERE subject_id=%s", (subject_id,))
        conn.commit()
        flash('Subject deleted.', 'info')
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        flash('Cannot delete subject: It is still linked to students or schedules.', 'error')
    except Exception as e:
        conn.rollback()
        print('delete_subject error (PostgreSQL):', e)
        flash('Failed to delete subject: ' + str(e), 'error') 
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_subject'))

@app.route('/enroll_student', methods=['POST'])
def enroll_student():
    subject_id = request.form.get('subject_id')
    student_id = request.form.get('student_id')
    
    if not (subject_id and student_id):
        flash('Subject and student are required.', 'error')
        return redirect(url_for('manage_subject'))
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME_STUDENT_SUBJECTS} (student_id, subject_id)
            VALUES (%s, %s)
        """, (int(student_id), int(subject_id)))
        conn.commit()
        flash('Student enrolled successfully.', 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash('Student already enrolled in this subject.', 'warning')
    except Exception as e:
        conn.rollback()
        print('enroll_student error (PostgreSQL):', e)
        flash('Failed to enroll student: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_subject'))

# --- FEE CONTROL (CONVERTED TO POSTGRESQL) ---
@app.route('/fee_control')
def fee_control():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    student = None
    student_fees = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        if q:
            search_id = None
            try:
                search_id = int(q)
            except ValueError:
                pass
            
            if search_id:
                # Search by ID (numeric) - Only students enrolled in subjects
                cursor.execute(f"""
                    SELECT DISTINCT s.id, s.name, sd.gender, sd.class, sd.phone
                    FROM {TABLE_NAME_STUDENT} s
                    LEFT JOIN {TABLE_NAME_STUDENT_DATA} sd ON s.id = sd.id
                    INNER JOIN {TABLE_NAME_STUDENT_SUBJECTS} ss ON s.id = ss.student_id
                    WHERE s.id = %s
                    LIMIT 1
                """, (search_id,))
            else:
                # Search by name - Only students enrolled in subjects
                cursor.execute(f"""
                    SELECT DISTINCT s.id, s.name, sd.gender, sd.class, sd.phone
                    FROM {TABLE_NAME_STUDENT} s
                    LEFT JOIN {TABLE_NAME_STUDENT_DATA} sd ON s.id = sd.id
                    INNER JOIN {TABLE_NAME_STUDENT_SUBJECTS} ss ON s.id = ss.student_id
                    WHERE s.name ILIKE %s
                    ORDER BY s.id
                    LIMIT 1
                """, (f"%{q}%",))
            
            row = cursor.fetchone()
            student = dict(row) if row else None
            
            if student:
                student_id = student['id']
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
                        t.name AS teacher_name
                    FROM {TABLE_NAME_STUDENT_SUBJECTS} ss
                    LEFT JOIN {TABLE_NAME_SUBJECT} sub ON ss.subject_id = sub.subject_id
                    LEFT JOIN {TABLE_NAME_TEACHER} t ON sub.teacher_id = t.id
                    LEFT JOIN {TABLE_NAME_FEES} f ON f.student_id = ss.student_id AND f.subject_id = ss.subject_id
                    WHERE ss.student_id = %s
                    ORDER BY sub.name
                """, (student_id,))
                student_fees = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("fee_control error:", e)
        student = None
        student_fees = None
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    
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
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        # PostgreSQL ON CONFLICT (unique constraint on student_id, subject_id)
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME_FEES} (student_id, subject_id, amount, due_date, status)
            VALUES (%s, %s, %s, %s, 'pending')
            ON CONFLICT (student_id, subject_id) DO UPDATE SET
                amount = EXCLUDED.amount,
                due_date = EXCLUDED.due_date,
                status = 'pending'
        """, (int(student_id), int(subject_id), float(amount) if amount else 0, due_date or None))
        conn.commit()
        flash('Fee added successfully.', 'success')
    except Exception as e:
        conn.rollback()
        print("add_fee error:", e)
        flash('Failed to add fee: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('fee_control', q=student_id))

@app.route('/pay_fee/<int:fee_id>', methods=['POST'])
def pay_fee(fee_id):
    amount_paid = request.form.get('amount_paid', 0)
    
    conn = None
    cursor = None
    fee = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        cursor.execute(f"SELECT student_id, amount, paid FROM {TABLE_NAME_FEES} WHERE fee_id=%s", (fee_id,))
        fee = dict(cursor.fetchone())
        
        if not fee:
            flash('Fee not found.', 'error')
            return redirect(url_for('fee_control'))
        
        new_paid = float(fee['paid']) + float(amount_paid)
        new_status = 'paid' if new_paid >= float(fee['amount']) else 'partial'
        
        cursor.execute(f"""
            UPDATE {TABLE_NAME_FEES} SET paid=%s, status=%s WHERE fee_id=%s
        """, (new_paid, new_status, fee_id))
        conn.commit()
        flash('Payment recorded successfully.', 'success')
    except Exception as e:
        conn.rollback()
        print("pay_fee error:", e)
        flash('Failed to record payment: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    
    student_id = fee.get('student_id') if fee else ''
    return redirect(url_for('fee_control', q=student_id))

@app.route('/delete_fee/<int:fee_id>', methods=['POST'])
def delete_fee(fee_id):
    conn = None
    cursor = None
    student_id = None
    fee = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        cursor.execute(f"SELECT student_id FROM {TABLE_NAME_FEES} WHERE fee_id=%s", (fee_id,))
        fee = dict(cursor.fetchone())
        if fee:
            student_id = fee['student_id']
        
        cursor.execute(f"DELETE FROM {TABLE_NAME_FEES} WHERE fee_id=%s", (fee_id,))
        conn.commit()
        flash('Fee deleted.', 'info')
    except Exception as e:
        conn.rollback()
        print("delete_fee error:", e)
        flash('Failed to delete fee: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('fee_control', q=student_id or ''))

# --- LOGOUT (UNCHANGED) ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    try:
        # Note: init_db() here is a placeholder. Ensure init_db.py is run on deployment.
        # init_db() 
        pass 
    except Exception as e:
        print("Failed to initialize database:", e)
        raise

    app.run(debug=True)
