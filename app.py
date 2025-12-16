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

# --- AUTHENTICATION (CHANGED TEMPLATE NAME) ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        role = request.form.get('role')
        conn = None
        cursor = None
        try:
            conn, cursor = get_db_conn(dict_cursor=True)
            
            if role == 'admin':
                table = TABLE_NAME_ADMIN
            elif role == 'student':
                table = TABLE_NAME_STUDENT
            elif role == 'teacher':
                table = TABLE_NAME_TEACHER
            else:
                flash('Invalid role selected.', 'error')
                return redirect(url_for('index'))

            # NOTE: We are using case-insensitive column names here: id, name, password
            cursor.execute(f"SELECT id, name, password FROM {table} WHERE name=%s", (name,))
            user = cursor.fetchone()
            
            if user and user['password'] == password:
                session['logged_in'] = True
                session['role'] = role
                session['name'] = user['name']
                session['user_id'] = user['id']
                flash(f'Logged in as {role.capitalize()}.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid name or password.', 'error')

        except Exception as e:
            print('Login error:', e)
            flash('An error occurred during login. Please try again.', 'error')
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    return render_template('index.html') # *** MODIFIED LINE: Changed 'login.html' to 'index.html' ***

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        flash('Please log in to access the dashboard.', 'info')
        return redirect(url_for('index'))
    
    role = session.get('role')
    user_name = session.get('name')
    user_id = session.get('user_id')
    
    if role == 'admin':
        return render_template('admin dashboard/dashboard.html', user_name=user_name, role=role)
    elif role == 'student':
        # Student Dashboard Logic
        conn = None
        cursor = None
        student_data = {}
        student_subjects = []
        try:
            conn, cursor = get_db_conn(dict_cursor=True)
            # Fetch student data
            cursor.execute(f"SELECT * FROM {TABLE_NAME_STUDENT} WHERE id=%s", (user_id,))
            student_data = cursor.fetchone() or {}
            
            # Fetch student's subjects and teacher/schedule info
            cursor.execute(f"""
                SELECT
                    s.subject_id, s.name as subject_name, t.name as teacher_name, t.id as teacher_id,
                    sc.class_time, sc.day_of_week
                FROM {TABLE_NAME_SUBJECT} s
                JOIN {TABLE_NAME_STUDENT_SUBJECTS} ss ON s.subject_id = ss.subject_id
                LEFT JOIN {TABLE_NAME_TEACHER} t ON s.teacher_id = t.id
                LEFT JOIN {TABLE_NAME_SCHEDULE} sc ON s.subject_id = sc.subject_id
                WHERE ss.student_id = %s
            """, (user_id,))
            student_subjects = cursor.fetchall()
            
        except Exception as e:
            print('Student dashboard error:', e)
            flash('Failed to load student data.', 'error')
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass
                
        return render_template('student dashboard/dashboard.html', user_name=user_name, role=role, student_data=student_data, subjects=student_subjects)
        
    elif role == 'teacher':
        # Teacher Dashboard Logic
        conn = None
        cursor = None
        teacher_subjects = []
        teacher_schedule = []
        try:
            conn, cursor = get_db_conn(dict_cursor=True)
            
            # Fetch subjects taught by the teacher
            cursor.execute(f"SELECT subject_id, name FROM {TABLE_NAME_SUBJECT} WHERE teacher_id=%s", (user_id,))
            subjects_list = cursor.fetchall()
            
            # Fetch schedules for the teacher's subjects
            subject_ids = [sub['subject_id'] for sub in subjects_list]
            if subject_ids:
                # Placeholder for dynamically creating the IN clause
                placeholders = ', '.join(['%s'] * len(subject_ids))
                cursor.execute(f"""
                    SELECT 
                        sc.schedule_id, sc.subject_id, sc.day_of_week, sc.class_time, s.name as subject_name
                    FROM {TABLE_NAME_SCHEDULE} sc
                    JOIN {TABLE_NAME_SUBJECT} s ON sc.subject_id = s.subject_id
                    WHERE sc.subject_id IN ({placeholders})
                    ORDER BY CASE 
                        WHEN day_of_week='Monday' THEN 1
                        WHEN day_of_week='Tuesday' THEN 2
                        WHEN day_of_week='Wednesday' THEN 3
                        WHEN day_of_week='Thursday' THEN 4
                        WHEN day_of_week='Friday' THEN 5
                        ELSE 6 END, class_time
                """, subject_ids)
                teacher_schedule = cursor.fetchall()
            
            # Prepare subject data
            for sub in subjects_list:
                # Fetch enrolled student count for each subject
                cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_STUDENT_SUBJECTS} WHERE subject_id=%s", (sub['subject_id'],))
                sub['student_count'] = cursor.fetchone()[0]
                teacher_subjects.append(sub)
                
        except Exception as e:
            print('Teacher dashboard error:', e)
            flash('Failed to load teacher data.', 'error')
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass
                
        return render_template('teacher dashboard/dashboard.html', 
                               user_name=user_name, 
                               role=role, 
                               subjects=teacher_subjects, 
                               schedule=teacher_schedule)

    else:
        flash('Unknown role.', 'error')
        return redirect(url_for('index'))

# --- ADMIN ROUTES (STUDENT MANAGEMENT) ---

@app.route('/manage_students')
def manage_students():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    students = []
    search_query = request.args.get('q')
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        sql = f"SELECT id, name, gender, class, grade, password, phone FROM {TABLE_NAME_STUDENT}"
        params = []
        
        if search_query:
            sql += " WHERE name ILIKE %s" # ILIKE for case-insensitive search in PostgreSQL
            params.append('%' + search_query + '%')
        
        cursor.execute(sql, params)
        students = cursor.fetchall()
        
    except Exception as e:
        print('manage_students error:', e)
        flash('Failed to retrieve students data: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/manage_students.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        class_ = request.form.get('class')
        grade = request.form.get('grade')
        password = request.form.get('password')
        phone = request.form.get('phone')

        conn = None
        cursor = None
        
        try:
            conn, cursor = get_db_conn(dict_cursor=True)
            
            # Find the max ID and assign the next available one
            cursor.execute(f"SELECT MAX(id) FROM {TABLE_NAME_STUDENT}")
            max_id = cursor.fetchone()[0]
            new_id = (max_id or 0) + 1

            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT} (id, name, gender, class, grade, password, phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (new_id, name, gender, class_, grade, password, phone)
            )
            conn.commit()

            flash('Student added successfully.', 'success')
            return redirect(url_for('manage_students'))
        except psycopg2.errors.UniqueViolation:
            flash('A student with this name already exists.', 'error')
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


@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    student = None
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # Fetch current student data
        cursor.execute(f"SELECT id, name, gender, class, grade, password, phone FROM {TABLE_NAME_STUDENT} WHERE id=%s", (id,))
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

            cursor.execute(
                f"""
                UPDATE {TABLE_NAME_STUDENT} 
                SET name=%s, gender=%s, class=%s, grade=%s, password=%s, phone=%s
                WHERE id=%s
                """,
                (name, gender, class_, grade, password, phone, id)
            )
            conn.commit()

            flash('Student updated successfully.', 'success')
            return redirect(url_for('manage_students'))

    except Exception as e:
        print('edit_student error:', e)
        flash('Failed to update student: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

    return render_template('admin dashboard/edit_student.html', student=student)

@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"DELETE FROM {TABLE_NAME_STUDENT} WHERE id=%s", (id,))
        conn.commit()
        flash('Student deleted successfully.', 'info')
    except Exception as e:
        print('delete_student error:', e)
        flash('Failed to delete student: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_students'))

# --- ADMIN ROUTES (TEACHER MANAGEMENT) ---

@app.route('/manage_teachers')
def manage_teachers():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    teachers = []
    search_query = request.args.get('q')

    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        sql = f"SELECT id, name, gender, password, phone FROM {TABLE_NAME_TEACHER}"
        params = []
        
        if search_query:
            sql += " WHERE name ILIKE %s"
            params.append('%' + search_query + '%')
        
        cursor.execute(sql, params)
        fetched_teachers = cursor.fetchall()

        for t in fetched_teachers:
            teacher_data = dict(t)
            # Fetch subjects taught by the teacher
            cursor.execute(f"SELECT name FROM {TABLE_NAME_SUBJECT} WHERE teacher_id=%s", (teacher_data['id'],))
            subjects = [sub['name'] for sub in cursor.fetchall()]
            teacher_data['subjects'] = ', '.join(subjects)
            teachers.append(teacher_data)
        
    except Exception as e:
        print('manage_teachers error:', e)
        flash('Failed to retrieve teachers data: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/manage_teachers.html', teachers=teachers)

@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        password = request.form.get('password')
        phone = request.form.get('phone')
        
        conn = None
        cursor = None
        
        try:
            conn, cursor = get_db_conn(dict_cursor=True)

            # Find the max ID and assign the next available one
            cursor.execute(f"SELECT MAX(id) FROM {TABLE_NAME_TEACHER}")
            max_id = cursor.fetchone()[0]
            new_id = (max_id or 0) + 1

            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_TEACHER} (id, name, gender, password, phone)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (new_id, name, gender, password, phone)
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
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

    return render_template('admin dashboard/add_teacher.html')

@app.route('/edit_teacher/<int:id>', methods=['GET', 'POST'])
def edit_teacher(id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    teacher = None
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # Fetch current teacher data
        cursor.execute(f"SELECT id, name, gender, password, phone FROM {TABLE_NAME_TEACHER} WHERE id=%s", (id,))
        teacher = cursor.fetchone()

        if not teacher:
            flash('Teacher not found.', 'error')
            return redirect(url_for('manage_teachers'))

        if request.method == 'POST':
            name = request.form.get('name')
            gender = request.form.get('gender')
            password = request.form.get('password')
            phone = request.form.get('phone')

            cursor.execute(
                f"""
                UPDATE {TABLE_NAME_TEACHER} 
                SET name=%s, gender=%s, password=%s, phone=%s
                WHERE id=%s
                """,
                (name, gender, password, phone, id)
            )
            conn.commit()

            flash('Teacher updated successfully.', 'success')
            return redirect(url_for('manage_teachers'))

    except Exception as e:
        print('edit_teacher error:', e)
        flash('Failed to update teacher: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

    return render_template('admin dashboard/edit_teacher.html', teacher=teacher)

@app.route('/delete_teacher/<int:id>', methods=['POST'])
def delete_teacher(id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"DELETE FROM {TABLE_NAME_TEACHER} WHERE id=%s", (id,))
        conn.commit()
        flash('Teacher deleted successfully.', 'info')
    except Exception as e:
        print('delete_teacher error:', e)
        flash('Failed to delete teacher: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_teachers'))


# --- ADMIN ROUTES (SUBJECT MANAGEMENT) ---

@app.route('/manage_subject')
def manage_subject():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    subjects = []
    all_students = []

    try:
        conn, cursor = get_db_conn(dict_cursor=True)

        # 1. Fetch all students (for the enrollment modal)
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_STUDENT} ORDER BY name")
        all_students = cursor.fetchall()
        
        # 2. Fetch all subjects with their assigned teacher and student count
        cursor.execute(f"""
            SELECT 
                s.subject_id, s.name, s.teacher_id, t.name as teacher_name, 
                COUNT(ss.student_id) as student_count
            FROM {TABLE_NAME_SUBJECT} s
            LEFT JOIN {TABLE_NAME_TEACHER} t ON s.teacher_id = t.id
            LEFT JOIN {TABLE_NAME_STUDENT_SUBJECTS} ss ON s.subject_id = ss.subject_id
            GROUP BY s.subject_id, s.name, s.teacher_id, t.name
            ORDER BY s.subject_id
        """)
        fetched_subjects = cursor.fetchall()
        
        # 3. For each subject, fetch enrolled students (for display on the manage page)
        for subject in fetched_subjects:
            sub = dict(subject)
            cursor.execute(f"""
                SELECT st.id, st.name 
                FROM {TABLE_NAME_STUDENT} st
                JOIN {TABLE_NAME_STUDENT_SUBJECTS} ss ON st.id = ss.student_id
                WHERE ss.subject_id = %s
            """, (sub['subject_id'],))
            sub['enrolled_students'] = cursor.fetchall()
            subjects.append(sub)

    except Exception as e:
        print('manage_subject error:', e)
        flash('Failed to retrieve subjects data: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    # Fetch all teachers for the subject form
    teachers = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY name")
        teachers = cursor.fetchall()
    except Exception as e:
        print('manage_subject teachers fetch error:', e)
        # Continue even if teachers fail to load
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/manage_subject.html', subjects=subjects, teachers=teachers, all_students=all_students)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    name = request.form.get('name')
    teacher_id = request.form.get('teacher_id') or None # Can be None if no teacher is selected
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        cursor.execute(
            f"""
            INSERT INTO {TABLE_NAME_SUBJECT} (name, teacher_id)
            VALUES (%s, %s)
            """,
            (name, teacher_id)
        )
        conn.commit()

        flash('Subject added successfully.', 'success')
    except psycopg2.errors.UniqueViolation:
        flash('A subject with this name already exists.', 'error')
    except Exception as e:
        print('add_subject error:', e)
        flash('Failed to add subject: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_subject'))

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    subject = None
    teachers = []

    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # Fetch current subject data
        cursor.execute(f"SELECT subject_id, name, teacher_id FROM {TABLE_NAME_SUBJECT} WHERE subject_id=%s", (subject_id,))
        subject = cursor.fetchone()

        if not subject:
            flash('Subject not found.', 'error')
            return redirect(url_for('manage_subject'))

        # Fetch all teachers for the form
        cursor.execute(f"SELECT id, name FROM {TABLE_NAME_TEACHER} ORDER BY name")
        teachers = cursor.fetchall()

        if request.method == 'POST':
            name = request.form.get('name')
            teacher_id = request.form.get('teacher_id') or None

            cursor.execute(
                f"""
                UPDATE {TABLE_NAME_SUBJECT} 
                SET name=%s, teacher_id=%s
                WHERE subject_id=%s
                """,
                (name, teacher_id, subject_id)
            )
            conn.commit()

            flash(f'Subject "{name}" updated successfully.', 'success')
            return redirect(url_for('manage_subject'))

    except Exception as e:
        print('edit_subject error:', e)
        flash('Failed to update subject: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

    return render_template('admin dashboard/edit_subject.html', subject=subject, teachers=teachers)

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"DELETE FROM {TABLE_NAME_SUBJECT} WHERE subject_id=%s", (subject_id,))
        conn.commit()
        flash('Subject deleted successfully.', 'info')
    except Exception as e:
        print('delete_subject error:', e)
        flash('Failed to delete subject: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_subject'))

@app.route('/enroll_student', methods=['POST'])
def enroll_student():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    subject_id = request.form.get('subject_id')
    student_id = request.form.get('student_id')
    
    if not (subject_id and student_id):
        flash('Subject and student are required.', 'error')
        return redirect(url_for('manage_subject'))
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        
        # Check if enrollment already exists (optional, but good practice)
        cursor.execute(f"""
            SELECT 1 FROM {TABLE_NAME_STUDENT_SUBJECTS} 
            WHERE student_id=%s AND subject_id=%s
        """, (student_id, subject_id))
        
        if cursor.fetchone():
            flash('Student already enrolled in this subject.', 'warning')
        else:
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_STUDENT_SUBJECTS} (student_id, subject_id)
                VALUES (%s, %s)
                """, (int(student_id), int(subject_id))
            )
            conn.commit()
            flash('Student enrolled successfully.', 'success')
            
    except Exception as e:
        print('enroll_student error:', e)
        flash('Failed to enroll student: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_subject'))

@app.route('/unenroll_student/<int:student_id>/<int:subject_id>', methods=['POST'])
def unenroll_student(student_id, subject_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(
            f"""
            DELETE FROM {TABLE_NAME_STUDENT_SUBJECTS} 
            WHERE student_id=%s AND subject_id=%s
            """, (student_id, subject_id)
        )
        conn.commit()
        flash('Student unenrolled successfully.', 'info')
    except Exception as e:
        print('unenroll_student error:', e)
        flash('Failed to unenroll student: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_subject'))


# --- ADMIN ROUTES (SCHEDULE MANAGEMENT) ---

@app.route('/manage_schedule', methods=['GET'])
def manage_schedule():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    schedules = []
    subjects = []
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # 1. Fetch all subjects for the form
        cursor.execute(f"SELECT subject_id, name FROM {TABLE_NAME_SUBJECT} ORDER BY name")
        subjects = cursor.fetchall()

        # 2. Fetch all schedules
        cursor.execute(f"""
            SELECT 
                sc.schedule_id, sc.day_of_week, sc.class_time, 
                sc.subject_id, s.name as subject_name, t.name as teacher_name
            FROM {TABLE_NAME_SCHEDULE} sc
            JOIN {TABLE_NAME_SUBJECT} s ON sc.subject_id = s.subject_id
            LEFT JOIN {TABLE_NAME_TEACHER} t ON s.teacher_id = t.id
            ORDER BY CASE 
                WHEN sc.day_of_week='Monday' THEN 1
                WHEN sc.day_of_week='Tuesday' THEN 2
                WHEN sc.day_of_week='Wednesday' THEN 3
                WHEN sc.day_of_week='Thursday' THEN 4
                WHEN sc.day_of_week='Friday' THEN 5
                ELSE 6 END, sc.class_time
        """)
        schedules = cursor.fetchall()

    except Exception as e:
        print('manage_schedule error:', e)
        flash('Failed to retrieve schedule data: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

    return render_template('admin dashboard/manage_schedule.html', schedules=schedules, subjects=subjects)

@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    subject_id = request.form.get('subject_id')
    day_of_week = request.form.get('day_of_week')
    class_time = request.form.get('class_time')
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        
        cursor.execute(
            f"""
            INSERT INTO {TABLE_NAME_SCHEDULE} (subject_id, day_of_week, class_time)
            VALUES (%s, %s, %s)
            """,
            (subject_id, day_of_week, class_time)
        )
        conn.commit()

        flash('Schedule added successfully.', 'success')
    except psycopg2.errors.UniqueViolation:
        flash('A schedule for this subject, day, and time already exists.', 'error')
    except Exception as e:
        print('add_schedule error:', e)
        flash('Failed to add schedule: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_schedule'))

@app.route('/delete_schedule/<int:schedule_id>', methods=['POST'])
def delete_schedule(schedule_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        cursor.execute(f"DELETE FROM {TABLE_NAME_SCHEDULE} WHERE schedule_id=%s", (schedule_id,))
        conn.commit()
        flash('Schedule deleted successfully.', 'info')
    except Exception as e:
        print('delete_schedule error:', e)
        flash('Failed to delete schedule: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('manage_schedule'))


# --- ADMIN ROUTES (FEES CONTROL) ---

@app.route('/fee_control', methods=['GET'])
def fee_control():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = None
    cursor = None
    students = []
    search_query = request.args.get('q')
    
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        sql = f"""
            SELECT 
                st.id, st.name, 
                COUNT(f.fee_id) AS total_fees, 
                SUM(f.amount) AS total_amount_due,
                SUM(f.paid) AS total_paid
            FROM {TABLE_NAME_STUDENT} st
            LEFT JOIN {TABLE_NAME_FEES} f ON st.id = f.student_id
        """
        params = []
        
        if search_query:
            sql += " WHERE st.name ILIKE %s OR st.id::text = %s"
            params.extend(['%' + search_query + '%', search_query])
            
        sql += " GROUP BY st.id, st.name ORDER BY st.name"
        
        cursor.execute(sql, params)
        students = cursor.fetchall()
        
        # Enhance data with fees breakdown
        for student in students:
            # Fetch all fees for the student
            cursor.execute(f"""
                SELECT 
                    f.fee_id, f.amount, f.paid, f.status, f.due_date, 
                    s.name as subject_name
                FROM {TABLE_NAME_FEES} f
                JOIN {TABLE_NAME_SUBJECT} s ON f.subject_id = s.subject_id
                WHERE f.student_id = %s
                ORDER BY f.due_date
            """, (student['id'],))
            student['fees_details'] = cursor.fetchall()
            
            # Calculate balance and status
            student['total_balance'] = (student['total_amount_due'] or 0) - (student['total_paid'] or 0)
            
            if student['total_balance'] <= 0 and student['total_fees'] > 0:
                student['payment_status'] = 'Paid'
            elif student['total_balance'] > 0 and student['total_paid'] > 0:
                student['payment_status'] = 'Partial'
            elif student['total_fees'] > 0:
                student['payment_status'] = 'Pending'
            else:
                student['payment_status'] = 'No Fees'


    except Exception as e:
        print('fee_control error:', e)
        flash('Failed to retrieve fees data: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    # Get all subjects for the fee assignment modal
    subjects_list = []
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        cursor.execute(f"SELECT subject_id, name FROM {TABLE_NAME_SUBJECT} ORDER BY name")
        subjects_list = cursor.fetchall()
    except Exception:
        pass
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return render_template('admin dashboard/fee_control.html', students=students, subjects=subjects_list)

@app.route('/add_fee', methods=['POST'])
def add_fee():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    student_id = request.form.get('student_id')
    subject_id = request.form.get('subject_id')
    amount = request.form.get('amount')
    due_date_str = request.form.get('due_date')
    
    if not (student_id and subject_id and amount and due_date_str):
        flash('All fields are required.', 'error')
        return redirect(url_for('fee_control', q=student_id or ''))

    try:
        amount = float(amount)
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid amount or date format.', 'error')
        return redirect(url_for('fee_control', q=student_id))

    conn = None
    cursor = None
    try:
        conn, cursor = get_db_conn()
        
        # Check for existing fee for this student and subject
        cursor.execute(f"""
            SELECT fee_id, amount, paid FROM {TABLE_NAME_FEES}
            WHERE student_id=%s AND subject_id=%s
        """, (student_id, subject_id))
        
        existing_fee = cursor.fetchone()
        
        if existing_fee:
            fee_id, old_amount, paid = existing_fee
            
            # If a record exists, update the amount and due date
            cursor.execute(f"""
                UPDATE {TABLE_NAME_FEES}
                SET amount=%s, due_date=%s, status=%s
                WHERE fee_id=%s
            """, (amount, due_date, 'paid' if amount <= paid else 'partial' if paid > 0 else 'pending', fee_id))
            flash('Existing fee updated successfully.', 'success')
            
        else:
            # If no record exists, insert a new one
            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME_FEES} (student_id, subject_id, amount, due_date)
                VALUES (%s, %s, %s, %s)
                """,
                (student_id, subject_id, amount, due_date)
            )
            flash('New fee assigned successfully.', 'success')

        conn.commit()
    except Exception as e:
        print('add_fee error:', e)
        flash('Failed to assign/update fee: ' + str(e), 'error')
        conn.rollback()
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
            
    return redirect(url_for('fee_control', q=student_id or ''))

@app.route('/make_payment/<int:fee_id>', methods=['POST'])
def make_payment(fee_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    payment_amount = request.form.get('payment_amount')
    student_id = None
    
    if not payment_amount:
        flash('Payment amount is required.', 'error')
        return redirect(url_for('fee_control'))
    
    try:
        payment_amount = float(payment_amount)
        if payment_amount <= 0:
            raise ValueError
    except ValueError:
        flash('Invalid payment amount.', 'error')
        return redirect(url_for('fee_control'))

    conn = None
    cursor = None
    fee = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # 1. Fetch current fee details
        cursor.execute(f"SELECT student_id, amount, paid FROM {TABLE_NAME_FEES} WHERE fee_id=%s", (fee_id,))
        fee = cursor.fetchone()
        
        if not fee:
            flash('Fee record not found.', 'error')
            return redirect(url_for('fee_control'))
        
        student_id = fee['student_id']
        new_paid = fee['paid'] + payment_amount
        
        if new_paid > fee['amount']:
            flash(f'Payment amount exceeds the remaining balance (${fee["amount"] - fee["paid"]:.2f}).', 'error')
            return redirect(url_for('fee_control', q=student_id))
            
        status = 'paid' if new_paid >= fee['amount'] else 'partial'
        
        # 2. Update the fee record
        cursor.execute(f"""
            UPDATE {TABLE_NAME_FEES}
            SET paid=%s, status=%s
            WHERE fee_id=%s
        """, (new_paid, status, fee_id))
        conn.commit()

        flash('Payment recorded successfully.', 'success')

    except Exception as e:
        print('make_payment error:', e)
        flash('Failed to record payment: ' + str(e), 'error')
        conn.rollback()
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
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    conn = None
    cursor = None
    student_id = None
    fee = None
    try:
        conn, cursor = get_db_conn(dict_cursor=True)
        
        # Fetch student_id before deletion for redirection
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
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialize the database before running the app if it's the main entry point
    try:
        # Note: In production (e.g., Render), you might use a separate script for init_db
        # But for simple deployment, running it here ensures tables exist.
        import init_db
        init_db.init_db()
        print("Database structure verified.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        # Continue running the app; connection errors will be caught later.
    
    app.run(debug=True)
