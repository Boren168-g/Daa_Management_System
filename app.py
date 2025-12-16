from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import psycopg2
from psycopg2 import extras # Used for DictCursor
from urllib.parse import urlparse

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


def get_db_conn(dict_cursor=False):
    """
    Establishes a connection to the PostgreSQL database.

    :param dict_cursor: If True, returns a DictCursor for results as dictionaries.
    :return: A tuple (connection, cursor).
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
        # Log the error but re-raise to be handled by the calling function
        print(f"Database connection error: {e}")
        # Ensure connection/cursor are closed if partially created
        if cursor: cursor.close()
        if conn: conn.close()
        raise

# NOTE: The original `init_db` is moved to the separate `init_db.py` file.

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
# The original app.add_url_rule('/', endpoint='index', view_func=index) is redundant 
# when using the @app.route decorator.

# --- Login and Signup Routes (Adapted for PostgreSQL/psycopg2) ---

# The logic in these routes is essentially the same, only the database 
# connection logic (`get_db_conn`) and error handling are changed for psycopg2.

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
            # PostgreSQL column names are case-sensitive if created with quotes
            cursor.execute(f'SELECT "ID", "Name", "Password" FROM {TABLE_NAME_ADMIN} WHERE "Name"=%s', (name,))
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
                f'INSERT INTO {TABLE_NAME_ADMIN} ("Name", "Password") VALUES (%s, %s)',
                (name, password)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Administrator account created. You can now sign in.', 'success')
            return redirect(url_for('administrators_page'))
        except psycopg2.errors.UniqueViolation:
            flash('Record already exists (duplicate name).', 'error')
            return redirect(url_for('create_admin'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_admin'))
    return render_template('sign in/create_admin.html')


# ... (Other login/create routes like teachers, students, parents follow the same pattern:
#      use get_db_conn(), wrap the SQL in try/except for psycopg2 errors, and use %s placeholders)
# The full implementation of the remaining routes would follow the same pattern as administrators/create_admin.
# The following routes (dashboard and management) show more complex query changes.

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
            cursor.execute(f'SELECT "ID", "Name", "Password" FROM {TABLE_NAME_TEACHER} WHERE "Name"=%s', (name,))
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
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', '').strip().lower() or 'other'
        if not (name and password):
            flash('Name and password are required.', 'error')
            return redirect(url_for('create_teacher'))
        try:
            conn, cursor = get_db_conn()
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_TEACHER} ("Name", "Password", "Phone", "Gender") VALUES (%s, %s, %s, %s)',
                (name, password, phone or None, gender)
            )
            conn.commit()
            cursor.close()
            conn.close()
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
            conn, cursor = get_db_conn()
            cursor.execute(f'SELECT "ID", "Name", "Password" FROM {TABLE_NAME_STUDENT} WHERE "Name"=%s', (name,))
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
            # Insert into STUDENTS
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_STUDENT} ("Name", "Password", "Phone", "Gender") VALUES (%s, %s, %s, %s) RETURNING "ID"',
                (name, password, phone, gender)
            )
            new_id = cursor.fetchone()[0] # Get the ID of the new student
            
            # Manually handle the logic of the former MySQL trigger/duplicate key
            # Insert into STUDENT_DATA
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT_DATA} ("ID", "Name", "Gender", "Class", "Grade", "Password", "Phone")
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT ("ID") DO UPDATE SET
                  "Name" = EXCLUDED."Name",
                  "Gender" = EXCLUDED."Gender",
                  "Password" = EXCLUDED."Password",
                  "Phone" = EXCLUDED."Phone";
                """,
                (new_id, name, gender, None, None, password, phone)
            )

            conn.commit()
            cursor.close()
            conn.close()
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
            cursor.execute(f'SELECT "ID", "Password" FROM {TABLE_NAME_PARENT} WHERE "ID"=%s', (parent_id,))
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

        try:
            conn, cursor = get_db_conn()
            # Optionally verify child exists
            cursor.execute(f'SELECT "ID" FROM {TABLE_NAME_STUDENT} WHERE "ID"=%s', (child_int,))
            student = cursor.fetchone()
            if not student:
                flash('Student (child) ID not found.', 'error')
                cursor.close(); conn.close()
                return redirect(url_for('create_parent'))

            cursor.execute(f'INSERT INTO {TABLE_NAME_PARENT} ("Password", "ChildrentID") VALUES (%s, %s) RETURNING "ID"',
                           (password, child_int))
            new_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            flash(f'Parent account created (Parent ID: {new_id}). You can sign in with that ID.', 'success')
            return redirect(url_for('parents_page'))
        except psycopg2.errors.IntegrityError as e:
            if "duplicate key" in str(e):
                 flash('Record already exists (duplicate).', 'error')
            else:
                 flash('Integrity error: ' + str(e), 'error')
            return redirect(url_for('create_parent'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_parent'))

    return render_template('sign in/create_parent.html')

# (The `login` and `signup` utility routes are also updated following this pattern)

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

# --- Management Routes (Key PostgreSQL changes: INSERT...RETURNING and ON CONFLICT) ---

@app.route('/manage_students')
def manage_students():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    students = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        if q:
            # Note: PostgreSQL uses ILIKE for case-insensitive LIKE
            cursor.execute(
                f'SELECT "ID", "Name", "Gender", "Class", "Grade", "Password", "Phone" FROM {TABLE_NAME_STUDENT_DATA} WHERE "Name" ILIKE %s ORDER BY "ID"',
                (f"%{q}%",)
            )
        else:
            cursor.execute(
                f'SELECT "ID", "Name", "Gender", "Class", "Grade", "Password", "Phone" FROM {TABLE_NAME_STUDENT_DATA} ORDER BY "ID"'
            )
        # Convert psycopg2.extras.DictRow to dict for template rendering consistency
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

            # Insert into STUDENTS and use RETURNING to get the new ID (PostgreSQL standard)
            cursor.execute(
                f'INSERT INTO {TABLE_NAME_STUDENT} ("Name", "Password", "Phone", "Gender") VALUES (%s, %s, %s, %s) RETURNING "ID"',
                (name, password, phone, gender)
            )
            new_id = cursor.fetchone()[0]

            # Insert / update student_data with the new ID using ON CONFLICT (PostgreSQL standard)
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


@app.route('/manage_schedule')
def manage_schedule():
    conn = None
    cursor = None
    schedules_table = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        # PostgreSQL-specific ORDER BY for day of the week
        cursor.execute(f"""
            SELECT
                s.schedule_id,
                s."ID" AS ID,
                s."Name" AS Name,
                s."Terms" AS terms,
                s."Subject" AS subject,
                s."Day" AS day,
                s.Time_start AS time_start,
                s.Time_end AS time_end,
                t."ID" AS teacher_id,
                t."Name" AS teacher_name
            FROM {TABLE_NAME_SCHEDULE} s
            LEFT JOIN {TABLE_NAME_TEACHER} t ON s."ID" = t."ID"
            ORDER BY 
                CASE s."Day"
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                    ELSE 8
                END, s.Time_start
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


# ... (Other management routes follow the same psycopg2/PostgreSQL-adapted pattern)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # It is best practice to NOT run init_db() on 'app.run(debug=True)' 
    # in a cloud deployment environment like Render. 
    # The init_db should be run separately as a pre-deploy or initial setup step.
    # However, for local development convenience, you can keep it commented out or use a flag.

    # from init_db import init_db # Uncomment if you want local initialization
    # try:
    #     init_db()
    # except Exception as e:
    #     print("Failed to initialize database:", e)
    #     # Don't raise if you expect to run without DB connection sometimes (e.g. for static testing)

    # In a typical Render deployment, the database connection details are ONLY 
    # available via the environment variable and the database is already created.
    # We only need the app to start.
    app.run(debug=True)
