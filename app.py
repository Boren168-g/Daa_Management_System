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
    # Using DictCursor is recommended for easy column access like row['column_name']
    cursor = conn.cursor(cursor_factory=extras.DictCursor) if dict_cursor else conn.cursor()
    return conn, cursor

# --- LOGIN UTILITY FUNCTION ---
def handle_login(identifier, password, role, table):
    """Generic function to handle login for any role."""
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # Determine the column to check based on the table
        id_column = 'name' 
        if table == TABLE_NAME_STUDENT or table == TABLE_NAME_PARENT:
            # Students are checked by 'name' (their unique username)
            # Parents are checked by 'student_id' (using 'name' field in form for student ID)
            id_column = 'id' if table == TABLE_NAME_STUDENT else 'student_id'
            
        
        # Check login credentials
        cursor.execute(f"SELECT id, name, password, student_id FROM {table} WHERE {id_column}=%s", (identifier,))
        user = cursor.fetchone()
        
        if user and user['password'] == password:
            session['logged_in'] = True
            session['role'] = role
            session['name'] = user['name'] if 'name' in user else identifier
            session['user_id'] = user['id']
            # For parents, also store the student_id for quick access
            if role == 'parent':
                session['student_id'] = user['student_id']

            flash(f'Logged in as {role.capitalize()}.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid ID or password.', 'error')
            # Render the specific login page again
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
        # Student login form uses 'name' for the student's unique name
        name = request.form.get('name') 
        password = request.form.get('password')
        return handle_login(name, password, 'student', TABLE_NAME_STUDENT)
    return render_template('students.html')


@app.route('/parents_page', methods=['GET', 'POST'])
def parents_page():
    """Handles Parent Login (by student ID)."""
    if request.method == 'POST':
        # Parent HTML form uses 'name' for the Child Student ID
        student_id = request.form.get('name') 
        password = request.form.get('password')
        # We search the parents table using the student_id
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

@app.route('/manage_students')
@role_required(['admin'])
def manage_students():
    conn = None
    cursor = None
    students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        # Assuming student data is combined for display
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


@app.route('/add_student', methods=['GET', 'POST'])
@role_required(['admin'])
def add_student():
    if request.method == 'POST':
        new_id = request.form.get('id')
        name = request.form.get('name')
        gender = request.form.get('gender')
        class_ = request.form.get('class')
        grade = request.form.get('grade')
        password = request.form.get('password')
        phone = request.form.get('phone')
        
        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()
            
            # 1. Insert into students table (main account)
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT} (id, name, password)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  password = EXCLUDED.password
                """,
                (new_id, name, password)
            )
            
            # 2. Insert into student_data table (details)
            # This uses ON CONFLICT for UPSERT functionality
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT_DATA} (id, gender, class, grade, phone)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  gender = EXCLUDED.gender,
                  class = EXCLUDED.class,
                  grade = EXCLUDED.grade,
                  phone = EXCLUDED.phone
                """,
                (new_id, gender, class_, grade, phone)
            )
            conn.commit()

            flash('Student added successfully.', 'success')
            return redirect(url_for('manage_students'))
        except psycopg2.errors.UniqueViolation as e:
            flash('Student ID or Name already exists.', 'error')
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


@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def edit_student(student_id):
    conn = None
    cursor = None
    student = None
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        # Fetch existing student data
        cursor.execute(f"""
            SELECT s.id, s.name, s.password, sd.gender, sd.class, sd.grade, sd.phone, sd.email 
            FROM {TABLE_NAME_STUDENT} s
            LEFT JOIN {TABLE_NAME_STUDENT_DATA} sd ON s.id = sd.id
            WHERE s.id = %s
        """, (student_id,))
        student = cursor.fetchone()
        
        if not student:
            flash('Student not found.', 'error')
            return redirect(url_for('manage_students'))
            
        if request.method == 'POST':
            name = request.form.get('name')
            gender = request.form.get('gender')
            class_ = request.form.get('class')
            grade = request.form.get('grade')
            password = request.form.get('password')
            phone = request.form.get('phone')
            email = request.form.get('email')

            # Update student main account
            cursor.execute(f"UPDATE {TABLE_NAME_STUDENT} SET name=%s, password=%s WHERE id=%s", 
                           (name, password, student_id))
            
            # Update student detail data (using UPSERT logic for safety)
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT_DATA} (id, gender, class, grade, phone, email)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  gender = EXCLUDED.gender,
                  class = EXCLUDED.class,
                  grade = EXCLUDED.grade,
                  phone = EXCLUDED.phone,
                  email = EXCLUDED.email
                """,
                (student_id, gender, class_, grade, phone, email)
            )
            
            conn.commit()
            flash('Student updated successfully.', 'success')
            return redirect(url_for('manage_students'))

    except Exception as e:
        conn.rollback()
        print('edit_student error:', e)
        flash('Failed to update student: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/edit_student.html', student=dict(student) if student else {})


@app.route('/delete_student/<int:student_id>', methods=['POST'])
@role_required(['admin'])
def delete_student(student_id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        # The CASCADE constraint in init_db.py will handle deleting related data (student_data, fees, etc.)
        cursor.execute(f"DELETE FROM {TABLE_NAME_STUDENT} WHERE id=%s", (student_id,))
        conn.commit()
        flash(f'Student ID {student_id} deleted successfully.', 'info')
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

# --- TEACHER ROUTES ---

@app.route('/manage_teachers')
@role_required(['admin'])
def manage_teachers():
    conn = None
    cursor = None
    teachers = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY id")
        teachers = cursor.fetchall()
    except Exception as e:
        print('manage_teachers error:', e)
        flash('Error retrieving teachers.', 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return render_template('admin dashboard/manage_teachers.html', teachers=teachers)


@app.route('/add_teacher', methods=['GET', 'POST'])
@role_required(['admin'])
def add_teacher():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()
            cursor.execute(f"INSERT INTO {TABLE_NAME_TEACHER} (name, password) VALUES (%s, %s)", (name, password))
            conn.commit()
            flash('Teacher added successfully.', 'success')
            return redirect(url_for('manage_teachers'))
        except psycopg2.errors.UniqueViolation:
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


@app.route('/edit_teacher/<int:teacher_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def edit_teacher(teacher_id):
    conn = None
    cursor = None
    teacher = None
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"SELECT id, name, password FROM {TABLE_NAME_TEACHER} WHERE id=%s", (teacher_id,))
        teacher = cursor.fetchone()

        if not teacher:
            flash('Teacher not found.', 'error')
            return redirect(url_for('manage_teachers'))
            
        if request.method == 'POST':
            name = request.form.get('name')
            password = request.form.get('password')

            cursor.execute(f"UPDATE {TABLE_NAME_TEACHER} SET name=%s, password=%s WHERE id=%s", 
                           (name, password, teacher_id))
            conn.commit()
            flash('Teacher updated successfully.', 'success')
            return redirect(url_for('manage_teachers'))

    except Exception as e:
        conn.rollback()
        print('edit_teacher error:', e)
        flash('Failed to update teacher: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/edit_teacher.html', teacher=dict(teacher) if teacher else {})


@app.route('/delete_teacher/<int:teacher_id>', methods=['POST'])
@role_required(['admin'])
def delete_teacher(teacher_id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        # The CASCADE constraint in init_db.py handles deleting related data (subjects, etc.)
        cursor.execute(f"DELETE FROM {TABLE_NAME_TEACHER} WHERE id=%s", (teacher_id,))
        conn.commit()
        flash(f'Teacher ID {teacher_id} deleted successfully.', 'info')
    except Exception as e:
        conn.rollback()
        print('delete_teacher error:', e)
        flash('Failed to delete teacher: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_teachers'))

# --- SUBJECT & SCHEDULE ROUTES ---

@app.route('/manage_subject', methods=['GET', 'POST'])
@role_required(['admin', 'teacher'])
def manage_subject():
    # Logic for managing subjects, teachers, and student enrollment
    conn = None
    cursor = None
    subjects = []
    teachers = []

    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # Add subject logic (POST)
        if request.method == 'POST' and 'subject_name' in request.form:
            subject_name = request.form.get('subject_name')
            teacher_id = request.form.get('teacher_id')
            description = request.form.get('description')

            cursor.execute(f"INSERT INTO {TABLE_NAME_SUBJECT} (subject_name, teacher_id, description) VALUES (%s, %s, %s)",
                           (subject_name, teacher_id if teacher_id else None, description))
            conn.commit()
            flash('Subject added successfully.', 'success')
            return redirect(url_for('manage_subject'))
        
        # Fetch subjects
        cursor.execute(f"""
            SELECT 
                s.subject_id, s.subject_name, s.description, 
                t.name AS teacher_name, t.id AS teacher_id, 
                (SELECT COUNT(*) FROM {TABLE_NAME_STUDENT_SUBJECTS} WHERE subject_id = s.subject_id) as enrolled_students
            FROM {TABLE_NAME_SUBJECT} s
            LEFT JOIN {TABLE_NAME_TEACHER} t ON s.teacher_id = t.id
            ORDER BY s.subject_name
        """)
        subjects = cursor.fetchall()

        # Fetch teachers for dropdown
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY name")
        teachers = cursor.fetchall()

    except Exception as e:
        conn.rollback()
        print('manage_subject error:', e)
        flash('An error occurred during subject management.', 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/manage_subject.html', subjects=subjects, teachers=teachers)


@app.route('/enroll_student', methods=['POST'])
@role_required(['admin', 'teacher'])
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
        cursor.execute("""
            INSERT INTO student_subjects (student_id, subject_id)
            VALUES (%s, %s)
            ON CONFLICT (student_id, subject_id) DO NOTHING
        """, (int(student_id), int(subject_id)))
        conn.commit()
        
        if cursor.rowcount > 0:
             flash('Student enrolled successfully.', 'success')
        else:
             flash('Student already enrolled in this subject.', 'warning')

    except Exception as e:
        conn.rollback()
        print('enroll_student error:', e)
        flash('Failed to enroll student: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_subject'))


@app.route('/manage_schedule', methods=['GET', 'POST'])
@role_required(['admin', 'teacher'])
def manage_schedule():
    conn = None
    cursor = None
    schedules = []
    subjects = []
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # Add schedule logic (POST)
        if request.method == 'POST' and 'class_name' in request.form:
            class_name = request.form.get('class_name')
            day_of_week = request.form.get('day_of_week')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            subject_id = request.form.get('subject_id')
            
            cursor.execute(f"""
                INSERT INTO {TABLE_NAME_SCHEDULE} (class_name, day_of_week, start_time, end_time, subject_id) 
                VALUES (%s, %s, %s, %s, %s)
            """, (class_name, day_of_week, start_time, end_time, subject_id))
            conn.commit()
            flash('Schedule added successfully.', 'success')
            return redirect(url_for('manage_schedule'))
            
        # Fetch all schedules
        cursor.execute(f"""
            SELECT s.schedule_id, s.class_name, s.day_of_week, s.start_time, s.end_time, sub.subject_name
            FROM {TABLE_NAME_SCHEDULE} s
            JOIN {TABLE_NAME_SUBJECT} sub ON s.subject_id = sub.subject_id
            ORDER BY s.day_of_week, s.start_time
        """)
        schedules = cursor.fetchall()
        
        # Fetch subjects for dropdown
        cursor.execute(f"SELECT subject_id, subject_name FROM {TABLE_NAME_SUBJECT} ORDER BY subject_name")
        subjects = cursor.fetchall()
        
    except Exception as e:
        conn.rollback()
        print('manage_schedule error:', e)
        flash('An error occurred during schedule management.', 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

    return render_template('admin dashboard/manage_schedule.html', schedules=schedules, subjects=subjects)


# --- FEE CONTROL ROUTES (Database interaction confirmed for PostgreSQL) ---

@app.route('/fee_control')
@role_required(['admin'])
def fee_control():
    # ... (rest of fee_control logic remains the same, using get_db_conn)
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    fees_data = []
    student = None
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        if q:
            # First, try to find the student by ID (assuming ID is integer)
            if q.isdigit():
                cursor.execute(f"SELECT id, name FROM {TABLE_NAME_STUDENT} WHERE id = %s", (int(q),))
                student = cursor.fetchone()
                # If not found by ID, try to find by name
                if not student:
                    cursor.execute(f"SELECT id, name FROM {TABLE_NAME_STUDENT} WHERE name ILIKE %s", (f'%{q}%',))
                    student = cursor.fetchone()
            # If search term is not a digit, search by name
            else:
                cursor.execute(f"SELECT id, name FROM {TABLE_NAME_STUDENT} WHERE name ILIKE %s", (f'%{q}%',))
                student = cursor.fetchone()

            if student:
                student_id = student['id']
                cursor.execute(f"""
                    SELECT f.fee_id, f.amount, f.paid, f.status, f.due_date, s.subject_name, s.subject_id
                    FROM {TABLE_NAME_FEES} f
                    JOIN {TABLE_NAME_SUBJECT} s ON f.subject_id = s.subject_id
                    WHERE f.student_id = %s
                    ORDER BY f.due_date
                """, (student_id,))
                fees_data = cursor.fetchall()
                student = dict(student) # Convert to dict if not already
            
    except Exception as e:
        print("fee_control error:", e)
        flash('Error retrieving fee data: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/fee_control.html', fees=fees_data, student=student, q=q)


@app.route('/add_fee/<int:student_id>', methods=['POST'])
@role_required(['admin'])
def add_fee(student_id):
    # ... (rest of add_fee logic remains the same, using get_db_conn)
    subject_id = request.form.get('subject_id')
    amount = request.form.get('amount')
    due_date = request.form.get('due_date')
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME_FEES} (student_id, subject_id, amount, due_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (student_id, subject_id) DO UPDATE SET
                amount = EXCLUDED.amount,
                due_date = EXCLUDED.due_date
        """, (student_id, subject_id, amount, due_date))
        conn.commit()
        flash('Fee added/updated successfully.', 'success')
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


@app.route('/update_fee/<int:fee_id>', methods=['POST'])
@role_required(['admin'])
def update_fee(fee_id):
    # ... (rest of update_fee logic remains the same, using get_db_conn)
    paid = request.form.get('paid')
    status = request.form.get('status')
    
    conn = None
    cursor = None
    fee = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        cursor.execute(f"UPDATE {TABLE_NAME_FEES} SET paid=%s, status=%s WHERE fee_id=%s RETURNING student_id", 
                       (paid, status, fee_id))
        conn.commit()
        
        fee = cursor.fetchone()
        flash('Fee updated successfully.', 'success')
    except Exception as e:
        conn.rollback()
        print("update_fee error:", e)
        flash('Failed to update fee: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    
    student_id = fee.get('student_id') if fee else ''
    return redirect(url_for('fee_control', q=student_id))


@app.route('/delete_fee/<int:fee_id>', methods=['POST'])
@role_required(['admin'])
def delete_fee(fee_id):
    # ... (rest of delete_fee logic remains the same, using get_db_conn)
    conn = None
    cursor = None
    student_id = None
    fee = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        cursor.execute(f"SELECT student_id FROM {TABLE_NAME_FEES} WHERE fee_id=%s", (fee_id,))
        fee = cursor.fetchone()
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
