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
# The DATABASE_URL is essential for Render deployment.
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
        # In a real app, this should log to a file or monitoring system
        print(f"Database connection error: {e}")
        # Ensure connection/cursor are closed if partially created
        if cursor: cursor.close()
        if conn: conn.close()
        raise # Re-raise the exception to be caught by the Flask route handler


# --- Core Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# --- FIX for werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'login' ---
@app.route('/login')
def login_router():
    """
    Routes the user to the correct role-specific login page based on the 
    'role' query parameter (e.g., /login?role=administrator).
    """
    role = request.args.get('role', 'administrator').lower()
    
    # Map the role parameter to the Flask endpoint name
    endpoint_map = {
        'administrator': 'administrators_page',
        'teacher': 'teachers_page',
        'student': 'students_page',
        'parent': 'parents_page'
    }
    
    target_endpoint = endpoint_map.get(role, 'administrators_page')
    
    # Redirect to the specific login page
    return redirect(url_for(target_endpoint))


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

# (The `teachers_page`, `create_teacher`, `students_page`, `create_student`, 
# `parents_page`, and `create_parent` routes would follow the same pattern 
# of using `get_db_conn` and handling `psycopg2` errors, as shown in the previous response.)

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
    # Only administrators can access this for security (add role check in real app)
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        sql = f'SELECT "ID", "Name", "Gender", "Class", "Grade", "Password", "Phone" FROM {TABLE_NAME_STUDENT_DATA}'
        if q:
            # PostgreSQL uses ILIKE for case-insensitive LIKE
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
            # This handles the logic that the original MySQL trigger was trying to perform.
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


@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    conn = None
    cursor = None
    student = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f'SELECT * FROM {TABLE_NAME_STUDENT_DATA} WHERE "ID"=%s', (student_id,))
        row = cursor.fetchone()
        if row:
            student = dict(row)
    except Exception as e:
        flash('Error fetching student data: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    if request.method == 'POST' and student:
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', 'other').strip().lower()
        class_ = request.form.get('class', '') or None
        grade = request.form.get('grade', None)
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip() or None

        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('edit_student', student_id=student_id))

        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn()
            
            # Update STUDENTS table
            cursor.execute(
                f"""
                UPDATE {TABLE_NAME_STUDENT} 
                SET "Name"=%s, "Password"=%s, "Phone"=%s, "Gender"=%s
                WHERE "ID"=%s
                """,
                (name, password, phone, gender, student_id)
            )
            
            # Update STUDENT_DATA table (Manually handle the logic of the former MySQL trigger)
            cursor.execute(
                f"""
                UPDATE {TABLE_NAME_STUDENT_DATA} 
                SET "Name"=%s, "Gender"=%s, "Class"=%s, "Grade"=%s, "Password"=%s, "Phone"=%s
                WHERE "ID"=%s
                """,
                (name, gender, class_, grade, password, phone, student_id)
            )

            conn.commit()
            flash('Student updated successfully.', 'success')
            return redirect(url_for('manage_students'))
        except psycopg2.errors.UniqueViolation:
            flash('Student name already exists.', 'error')
            return redirect(url_for('edit_student', student_id=student_id))
        except Exception as e:
            flash('Failed to update student: ' + str(e), 'error')
            return redirect(url_for('edit_student', student_id=student_id))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('manage_students'))

    return render_template('admin dashboard/edit_student.html', student=student)


@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        # Due to ON DELETE CASCADE on the foreign key, deleting from STUDENTS
        # will automatically delete related records in STUDENT_DATA, FEES, etc.
        cursor.execute(f'DELETE FROM {TABLE_NAME_STUDENT} WHERE "ID"=%s', (student_id,))
        conn.commit()
        flash('Student deleted successfully.', 'success')
    except Exception as e:
        print('delete_student error:', e)
        flash('Failed to delete student: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_students'))


# --- Fee Control Example (Adapted) ---

@app.route('/fee_control')
def fee_control():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    fees_list = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        sql = f"""
            SELECT 
                f.*, s."Name" AS student_name, subj.name AS subject_name 
            FROM {TABLE_NAME_FEES} f
            JOIN {TABLE_NAME_STUDENT} s ON f.student_id = s."ID"
            JOIN {TABLE_NAME_SUBJECT} subj ON f.subject_id = subj.subject_id
        """
        if q and q.isdigit():
            # Search by student ID
            sql += ' WHERE f.student_id = %s'
            cursor.execute(sql, (int(q),))
        elif q:
            # Search by student name (PostgreSQL ILIKE)
            sql += ' WHERE s."Name" ILIKE %s'
            cursor.execute(sql, (f"%{q}%",))
        else:
            cursor.execute(sql)
            
        fees_list = [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        print("fee_control error:", e)
        flash('Failed to load fees: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    
    return render_template('admin dashboard/fee_control.html', fees_list=fees_list, q=q)


@app.route('/update_fee_status', methods=['POST'])
def update_fee_status():
    fee_id = request.form.get('fee_id')
    new_status = request.form.get('status')
    amount_paid_str = request.form.get('amount_paid')
    student_id = request.form.get('student_id') # To redirect back

    if not (fee_id and new_status):
        flash('Missing fee ID or status.', 'error')
        return redirect(url_for('fee_control', q=student_id or ''))

    conn = None
    cursor = None
    try:
        amount_paid = float(amount_paid_str) if amount_paid_str else 0.00
        
        conn, cursor = get_db_conn()
        
        # 1. Update the 'paid' amount
        cursor.execute(f'UPDATE {TABLE_NAME_FEES} SET paid = %s WHERE fee_id = %s', 
                       (amount_paid, int(fee_id)))
                       
        # 2. Get the updated amount and total amount to determine status
        cursor.execute(f'SELECT amount, paid FROM {TABLE_NAME_FEES} WHERE fee_id = %s', (int(fee_id),))
        row = cursor.fetchone()
        
        if row:
            total_amount, paid_amount = row
            status_to_set = new_status
            
            if paid_amount >= total_amount:
                status_to_set = 'paid'
            elif paid_amount > 0 and paid_amount < total_amount:
                status_to_set = 'partial'
            else:
                status_to_set = 'pending'
                
            # 3. Update the status based on calculated logic
            cursor.execute(f'UPDATE {TABLE_NAME_FEES} SET status = %s WHERE fee_id = %s', 
                           (status_to_set, int(fee_id)))
            
            conn.commit()
            flash(f'Fee status for ID {fee_id} updated to {status_to_set}.', 'success')
        else:
            flash('Fee record not found.', 'error')
            
    except ValueError:
        flash('Invalid amount paid value.', 'error')
    except Exception as e:
        print('update_fee_status error:', e)
        flash('Failed to update fee status: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('fee_control', q=student_id or ''))


# ... (All other routes must be converted using get_db_conn and PostgreSQL syntax)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Reminder: Use gunicorn for production on Render (gunicorn app:app)
    # The init_db should be run separately (see init_db.py)
    app.run(debug=True)
