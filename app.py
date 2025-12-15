from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_CONF = {
    "host": "localhost",
    "user": "root",
    "password": ""
}
DB_NAME = "daa_management_system"
TABLE_NAME_ADMIN = "administrators"
TABLE_NAME_STUDENT = "students"
TABLE_NAME_TEACHER = "teachers"
TABLE_NAME_PARENT = "parents"
TABLE_NAME_STUDENT_DATA = "student_data"
TABLE_NAME_SCHEDULE = "schedules_table"
TABLE_NAME_SUBJECT = "subjects"

def init_db():
    tmp = None
    conn = None
    try:
        tmp = mysql.connector.connect(**DB_CONF)
        tmp_cursor = tmp.cursor()
        tmp_cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        tmp_cursor.close()
        tmp.close()

        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(buffered=True)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME_ADMIN}` (
                `ID` INT AUTO_INCREMENT PRIMARY KEY,
                `Name` VARCHAR(255) NOT NULL,
                `Password` VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME_STUDENT}` (
                `ID` INT AUTO_INCREMENT PRIMARY KEY,
                `Name` VARCHAR(255) NOT NULL,
                `Password` VARCHAR(255) NOT NULL,
                `Phone` VARCHAR(50),
                `Gender` ENUM('male','female','other') DEFAULT 'other'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME_TEACHER}` (
                `ID` INT AUTO_INCREMENT PRIMARY KEY,
                `Name` VARCHAR(255) NOT NULL,
                `Password` VARCHAR(255) NOT NULL,
                `Phone` VARCHAR(50),
                `Gender` ENUM('male','female','other') DEFAULT 'other'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME_PARENT}` (
                `ID` INT AUTO_INCREMENT PRIMARY KEY,
                `Password` VARCHAR(255) NOT NULL,
                `ChildrentID` INT,
                CONSTRAINT `fk_parent_child` FOREIGN KEY (`ChildrentID`)
                    REFERENCES `{TABLE_NAME_STUDENT}` (`ID`)
                    ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME_STUDENT_DATA}` (
                `ID` INT PRIMARY KEY,
                `Name` VARCHAR(255) NOT NULL,
                `Gender` ENUM('male','female','other') DEFAULT 'other',
                `Class` VARCHAR(50),
                `Grade` VARCHAR(10),
                `Password` VARCHAR(255) NOT NULL,
                `Phone` VARCHAR(50),
                CONSTRAINT `fk_student_data` FOREIGN KEY (`ID`)
                    REFERENCES `{TABLE_NAME_STUDENT}` (`ID`)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute(f"""
            INSERT INTO `{TABLE_NAME_STUDENT_DATA}` (`ID`,`Name`,`Gender`,`Password`,`Phone`)
            SELECT ID, Name, Gender, Password, Phone FROM `{TABLE_NAME_STUDENT}`
            ON DUPLICATE KEY UPDATE
                `Name` = VALUES(`Name`),
                `Gender` = VALUES(`Gender`),
                `Password` = VALUES(`Password`),
                `Phone` = VALUES(`Phone`);
        """)
        cursor.execute("DROP TRIGGER IF EXISTS trg_students_after_insert;")
        cursor.execute("DROP TRIGGER IF EXISTS trg_students_after_update;")
        cursor.execute("DROP TRIGGER IF EXISTS trg_students_after_delete;")
        cursor.execute(f"""
        CREATE TRIGGER trg_students_after_insert
        AFTER INSERT ON `{TABLE_NAME_STUDENT}`
        FOR EACH ROW
        BEGIN
            INSERT INTO `{TABLE_NAME_STUDENT_DATA}` (`ID`,`Name`,`Gender`,`Password`,`Phone`)
            VALUES (NEW.ID, NEW.Name, NEW.Gender, NEW.Password, NEW.Phone);
        END;
        """)
        cursor.execute(f"""
        CREATE TRIGGER trg_students_after_update
        AFTER UPDATE ON `{TABLE_NAME_STUDENT}`
        FOR EACH ROW
        BEGIN
            UPDATE `{TABLE_NAME_STUDENT_DATA}`
            SET `Name` = NEW.Name,
                `Gender` = NEW.Gender,
                `Password` = NEW.Password,
                `Phone` = NEW.Phone
            WHERE `ID` = NEW.ID;
        END;
        """)
        cursor.execute(f"""
        CREATE TRIGGER trg_students_after_delete
        AFTER DELETE ON `{TABLE_NAME_STUDENT}`
        FOR EACH ROW
        BEGIN
            DELETE FROM `{TABLE_NAME_STUDENT_DATA}` WHERE `ID` = OLD.ID;
        END;
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME_SCHEDULE}` (
                `schedule_id` INT AUTO_INCREMENT PRIMARY KEY,
                `ID` INT NOT NULL,
                `Name` VARCHAR(255),
                `Terms` VARCHAR(100),
                `Subject` VARCHAR(255) NOT NULL,
                `Day` VARCHAR(20) NOT NULL,
                `Time_start` TIME NOT NULL,
                `Time_end` TIME NOT NULL,
                KEY `fk_ID` (`ID`),
                CONSTRAINT `fk_schedule_teacher` FOREIGN KEY (`ID`) REFERENCES `{TABLE_NAME_TEACHER}` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{TABLE_NAME_SUBJECT}` (
                `subject_id` INT AUTO_INCREMENT PRIMARY KEY,
                `name` VARCHAR(255) NOT NULL,
                `teacher_id` INT,
                CONSTRAINT `fk_subject_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `{TABLE_NAME_TEACHER}` (`ID`) ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `fees` (
                `fee_id` INT AUTO_INCREMENT PRIMARY KEY,
                `student_id` INT NOT NULL,
                `subject_id` INT NOT NULL,
                `amount` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                `paid` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                `status` ENUM('pending', 'partial', 'paid') DEFAULT 'pending',
                `due_date` DATE,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT `fk_fee_student` FOREIGN KEY (`student_id`) REFERENCES `{TABLE_NAME_STUDENT}` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT `fk_fee_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `student_subjects` (
                `enrollment_id` INT AUTO_INCREMENT PRIMARY KEY,
                `student_id` INT NOT NULL,
                `subject_id` INT NOT NULL,
                `enrolled_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY `unique_enrollment` (`student_id`, `subject_id`),
                CONSTRAINT `fk_enrollment_student` FOREIGN KEY (`student_id`) 
                    REFERENCES `{TABLE_NAME_STUDENT}` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT `fk_enrollment_subject` FOREIGN KEY (`subject_id`) 
                    REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        try:
            if tmp and tmp.is_connected():
                tmp.close()
        except Exception:
            pass
        try:
            if conn and conn.is_connected():
                conn.close()
        except Exception:
            pass
        print("Database initialization error:", e)
        raise

def get_db_conn(dict_cursor=False):
    conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
    cursor = conn.cursor(dictionary=dict_cursor, buffered=True)
    return conn, cursor
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
app.add_url_rule('/', endpoint='index', view_func=index)

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
            cursor.execute(f"SELECT ID, Name, Password FROM `{TABLE_NAME_ADMIN}` WHERE Name=%s", (name,))
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
                f"INSERT INTO `{TABLE_NAME_ADMIN}` (Name, Password) VALUES (%s, %s)",
                (name, password)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Administrator account created. You can now sign in.', 'success')
            return redirect(url_for('administrators_page'))
        except mysql.connector.IntegrityError:
            flash('Record already exists (duplicate).', 'error')
            return redirect(url_for('create_admin'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_admin'))
    return render_template('sign in/create_admin.html')

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
            cursor.execute(f"SELECT ID, Name, Password FROM `{TABLE_NAME_TEACHER}` WHERE Name=%s", (name,))
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
                f"INSERT INTO `{TABLE_NAME_TEACHER}` (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                (name, password, phone or None, gender)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Teacher account created. You can now sign in.', 'success')
            return redirect(url_for('teachers_page'))
        except mysql.connector.IntegrityError:
            flash('Record already exists (duplicate).', 'error')
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
            cursor.execute(f"SELECT ID, Name, Password FROM `{TABLE_NAME_STUDENT}` WHERE Name=%s", (name,))
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
                f"INSERT INTO `{TABLE_NAME_STUDENT}` (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                (name, password, phone, gender)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Student account created. You can now sign in.', 'success')
            return redirect(url_for('students_page'))
        except mysql.connector.IntegrityError:
            flash('Record already exists (duplicate).', 'error')
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
            cursor.execute(f"SELECT ID, Password FROM `{TABLE_NAME_PARENT}` WHERE ID=%s", (parent_id,))
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
            cursor.execute(f"SELECT ID FROM `{TABLE_NAME_STUDENT}` WHERE ID=%s", (child_int,))
            student = cursor.fetchone()
            if not student:
                flash('Student (child) ID not found.', 'error')
                cursor.close(); conn.close()
                return redirect(url_for('create_parent'))

            cursor.execute(f"INSERT INTO `{TABLE_NAME_PARENT}` (Password, ChildrentID) VALUES (%s, %s)",
                           (password, child_int))
            conn.commit()
            new_id = cursor.lastrowid
            cursor.close()
            conn.close()
            flash(f'Parent account created (Parent ID: {new_id}). You can sign in with that ID.', 'success')
            return redirect(url_for('parents_page'))
        except mysql.connector.IntegrityError:
            flash('Record already exists (duplicate).', 'error')
            return redirect(url_for('create_parent'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('create_parent'))

    return render_template('sign in/create_parent.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get('role', '').lower()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        if not (name and password):
            flash('All fields are required.', 'error')
            return redirect(url_for('login', role=role))
        table = {
            'administrator': TABLE_NAME_ADMIN,
            'teacher': TABLE_NAME_TEACHER,
            'student': TABLE_NAME_STUDENT,
            'parent': TABLE_NAME_PARENT
        }.get(role, None)

        try:
            conn, cursor = get_db_conn()
            if table is None:
                cursor.execute(f"SELECT ID, Name, Password FROM `{TABLE_NAME_ADMIN}` WHERE Name=%s", (name,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute(f"SELECT ID, Name, Password FROM `{TABLE_NAME_TEACHER}` WHERE Name=%s", (name,))
                    row = cursor.fetchone()
                if not row:
                    cursor.execute(f"SELECT ID, Name, Password FROM `{TABLE_NAME_STUDENT}` WHERE Name=%s", (name,))
                    row = cursor.fetchone()
                if not row:
                    flash('Invalid credentials.', 'error')
                    cursor.close(); conn.close()
                    return redirect(url_for('login'))
                user_id, user_name, db_password = row
            else:
                if table == TABLE_NAME_PARENT:
                    try:
                        parent_id = int(name)
                    except ValueError:
                        flash('For parent login enter numeric Parent ID.', 'error')
                        cursor.close(); conn.close()
                        return redirect(url_for('login', role=role))
                    cursor.execute(f"SELECT ID, Password FROM `{table}` WHERE ID=%s", (parent_id,))
                    prow = cursor.fetchone()
                    if not prow:
                        flash('Invalid credentials.', 'error')
                        cursor.close(); conn.close()
                        return redirect(url_for('login', role=role))
                    user_id = prow[0]; user_name = f"Parent#{user_id}"; db_password = prow[1]
                else:
                    cursor.execute(f"SELECT ID, Name, Password FROM `{table}` WHERE Name=%s", (name,))
                    trow = cursor.fetchone()
                    if not trow:
                        flash('Invalid credentials.', 'error')
                        cursor.close(); conn.close()
                        return redirect(url_for('login', role=role))
                    user_id, user_name, db_password = trow
            if password == db_password:
                session['user_name'] = user_name
                session['user_role'] = role or 'user'
                cursor.close(); conn.close()
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials.', 'error')
                cursor.close(); conn.close()
                return redirect(url_for('login', role=role))

        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('login', role=role))

    tmpl = ROLE_TEMPLATES.get(role, 'login.html')
    return render_template(tmpl, role=role)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    role = request.args.get('role', '').lower()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', '').strip().lower() or 'other'
        child_id = request.form.get('child_id', '').strip()

        if role == 'parent':
            if not (password and child_id):
                flash('Child ID and password required for parent signup.', 'error')
                return redirect(url_for('signup', role=role))
        else:
            if not (name and password):
                flash('Name and password required.', 'error')
                return redirect(url_for('signup', role=role))

        try:
            conn, cursor = get_db_conn()
            if role == 'administrator':
                cursor.execute(f"INSERT INTO `{TABLE_NAME_ADMIN}` (Name, Password) VALUES (%s, %s)", (name, password))
            elif role == 'teacher':
                cursor.execute(f"INSERT INTO `{TABLE_NAME_TEACHER}` (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                               (name, password, phone or None, gender))
            elif role == 'student':
                cursor.execute(f"INSERT INTO `{TABLE_NAME_STUDENT}` (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                               (name, password, phone or None, gender))
            elif role == 'parent':
                try:
                    child_int = int(child_id)
                except ValueError:
                    child_int = None
                cursor.execute(f"INSERT INTO `{TABLE_NAME_PARENT}` (Password, ChildrentID) VALUES (%s, %s)",
                               (password, child_int))
            else:
                flash('Unknown role for signup.', 'error')
                cursor.close(); conn.close()
                return redirect(url_for('signup', role=role))

            conn.commit()
            cursor.close()
            conn.close()
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('login', role=role))
        except mysql.connector.IntegrityError:
            flash('Record already exists (duplicate).', 'error')
            return redirect(url_for('signup', role=role))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return redirect(url_for('signup', role=role))

    tmpl = SIGNUP_TEMPLATES.get(role, 'signup.html')
    return render_template(tmpl, role=role)

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

@app.route('/manage_students')
def manage_students():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    students = []
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        if q:
            cursor.execute(
                f"SELECT ID, Name, Gender, `Class`, `Grade`, Password, Phone FROM `{TABLE_NAME_STUDENT_DATA}` WHERE `Name` LIKE %s ORDER BY ID",
                (f"%{q}%",)
            )
        else:
            cursor.execute(
                f"SELECT ID, Name, Gender, `Class`, `Grade`, Password, Phone FROM `{TABLE_NAME_STUDENT_DATA}` ORDER BY ID"
            )
        students = cursor.fetchall()
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
            conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
            cursor = conn.cursor()

            # Insert into students to get auto-increment ID
            cursor.execute(
                f"INSERT INTO `{TABLE_NAME_STUDENT}` (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                (name, password, phone, gender)
            )
            conn.commit()
            new_id = cursor.lastrowid

            # Insert / update student_data with same ID
            cursor.execute(
                f"""
                INSERT INTO `{TABLE_NAME_STUDENT_DATA}` (`ID`,`Name`,`Gender`,`Class`,`Grade`,`Password`,`Phone`)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  `Name`=VALUES(`Name`),
                  `Gender`=VALUES(`Gender`),
                  `Class`=VALUES(`Class`),
                  `Grade`=VALUES(`Grade`),
                  `Password`=VALUES(`Password`),
                  `Phone`=VALUES(`Phone`)
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

@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM `{TABLE_NAME_STUDENT_DATA}` WHERE `ID`=%s", (id,))
        cursor.execute(f"DELETE FROM `{TABLE_NAME_STUDENT}` WHERE `ID`=%s", (id,))

        conn.commit()
        flash('Student deleted successfully.', 'info')
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

@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            gender = request.form.get('gender', 'other')
            class_ = request.form.get('class', '') or None
            password = request.form.get('password', '')
            phone = request.form.get('phone', '')
            
            cursor.execute(
                f"UPDATE `{TABLE_NAME_STUDENT_DATA}` SET `Name`=%s, `Gender`=%s, `Class`=%s, `Password`=%s, `Phone`=%s WHERE `ID`=%s",
                (name, gender, class_, password, phone, id)
            )
            conn.commit()
            flash('Student updated successfully.', 'success')
            return redirect(url_for('manage_students'))

        # GET request - fetch student data
        cursor.execute(
            f"SELECT ID, Name, Gender, `Class`, `Grade`, Password, Phone FROM `{TABLE_NAME_STUDENT_DATA}` WHERE ID=%s",
            (id,)
        )
        student = cursor.fetchone()
        
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

@app.route('/manage_teachers')
def manage_teachers():
    conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.*, GROUP_CONCAT(s.name SEPARATOR ', ') AS subjects
        FROM teachers t
        LEFT JOIN subjects s ON t.ID = s.teacher_id
        GROUP BY t.ID
        ORDER BY t.Name
    """)
    teachers = cursor.fetchall()
    cursor.close()
    conn.close()
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
            conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO `{TABLE_NAME_TEACHER}` (Name, Password, Phone, Gender) VALUES (%s, %s, %s, %s)",
                (name, password, phone, gender)
            )
            conn.commit()
            flash('Teacher added successfully.', 'success')
            return redirect(url_for('manage_teachers'))
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
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            gender = request.form.get('gender', 'other')
            password = request.form.get('password', '')
            phone = request.form.get('phone', '')
            cursor.execute(
                f"UPDATE `{TABLE_NAME_TEACHER}` SET `Name`=%s, `Gender`=%s, `Password`=%s, `Phone`=%s WHERE `ID`=%s",
                (name, gender, password, phone, id)
            )
            conn.commit()
            flash('Teacher updated successfully.', 'success')
            return redirect(url_for('manage_teachers'))

        cursor.execute(
            f"SELECT ID, Name, Gender, Phone, Password FROM `{TABLE_NAME_TEACHER}` WHERE ID=%s",
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
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass

@app.route('/delete_teacher/<int:id>', methods=['GET','POST'])
def delete_teacher(id):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM `{TABLE_NAME_TEACHER}` WHERE `ID`=%s", (id,))
        conn.commit()
        flash('Teacher deleted successfully.', 'info')
    except Exception as e:
        print('delete_teacher error:', e)
        flash('Failed to delete teacher.', 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_teachers'))

@app.route('/manage_schedule')
def manage_schedule():
    conn = None
    cursor = None
    schedules_table = []
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
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
            FROM `{TABLE_NAME_SCHEDULE}` s
            LEFT JOIN `{TABLE_NAME_TEACHER}` t ON s.ID = t.ID
            ORDER BY FIELD(s.Day, 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'), s.Time_start
        """)
        schedules_table = cursor.fetchall()
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
            conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO `{TABLE_NAME_SCHEDULE}` 
                  (`ID`, `Name`, `Terms`, `Subject`, `Day`, `Time_start`, `Time_end`)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (int(teacher_id), teacher_name, terms, subject, day, time_start, time_end))
            conn.commit()
            return redirect(url_for('manage_schedule'))
        except Exception as e:
            print('add_schedule error:', e)
            return redirect(url_for('add_schedule'))
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT ID, Name FROM `{TABLE_NAME_TEACHER}` ORDER BY Name")
        teachers = cursor.fetchall()
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
            conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE `{TABLE_NAME_SCHEDULE}`
                SET `ID`=%s, `Name`=%s, `Terms`=%s, `Subject`=%s, 
                    `Day`=%s, `Time_start`=%s, `Time_end`=%s
                WHERE `ID`=%s
            """, (int(teacher_id), teacher_name, terms, subject, day, time_start, time_end, id))
            conn.commit()
            flash('Schedule updated successfully.', 'success')
            return redirect(url_for('manage_schedule'))
        except Exception as e:
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
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM `{TABLE_NAME_SCHEDULE}` WHERE `ID`=%s", (id,))
        schedule = cursor.fetchone()
        cursor.execute(f"SELECT ID, Name FROM `{TABLE_NAME_TEACHER}` ORDER BY Name")
        teachers = cursor.fetchall()
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
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM `{TABLE_NAME_SCHEDULE}` WHERE `ID` = %s", (id,))
        conn.commit()
        flash('Schedule deleted.', 'info')
    except Exception as e:
        print('delete_schedule error:', e)
        flash('Failed to delete schedule: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_schedule'))

@app.route('/manage_subject')
def manage_subject():
    conn, cursor = get_db_conn(dict_cursor=True)
    cursor.execute("""
        SELECT s.subject_id, s.name, t.Name AS teacher_name,
               COUNT(ss.student_id) AS student_count
        FROM subjects s
        LEFT JOIN teachers t ON s.teacher_id = t.ID
        LEFT JOIN student_subjects ss ON s.subject_id = ss.subject_id
        GROUP BY s.subject_id, s.name, t.Name
        ORDER BY s.subject_id
    """)
    subjects = cursor.fetchall()
    
    # Get enrolled students for each subject
    for subject in subjects:
        cursor.execute("""
            SELECT s.ID, s.Name
            FROM students s
            INNER JOIN student_subjects ss ON s.ID = ss.student_id
            WHERE ss.subject_id = %s
            ORDER BY s.Name
        """, (subject['subject_id'],))
        subject['enrolled_students'] = cursor.fetchall()
    
    cursor.execute(f"SELECT ID, Name FROM `{TABLE_NAME_TEACHER}` ORDER BY Name")
    teachers = cursor.fetchall()
    
    cursor.execute(f"SELECT ID, Name FROM `{TABLE_NAME_STUDENT}` ORDER BY Name")
    all_students = cursor.fetchall()
    
    cursor.close(); conn.close()
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
    conn, cursor = get_db_conn()
    cursor.execute("INSERT INTO subjects (name, teacher_id) VALUES (%s, %s)", (name, teacher_id if teacher_id else None))
    conn.commit()
    cursor.close(); conn.close()
    flash('Subject added.', 'success')
    return redirect(url_for('manage_subject'))

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    conn, cursor = get_db_conn(dict_cursor=True)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        teacher_id = request.form.get('teacher_id') or None
        cursor.execute("UPDATE subjects SET name=%s, teacher_id=%s WHERE subject_id=%s", (name, teacher_id if teacher_id else None, subject_id))
        conn.commit()
        cursor.close(); conn.close()
        flash('Subject updated.', 'success')
        return redirect(url_for('manage_subject'))
    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (subject_id,))
    subject = cursor.fetchone()
    cursor.execute(f"SELECT ID, Name FROM `{TABLE_NAME_TEACHER}` ORDER BY Name")
    teachers = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('admin dashboard/edit_subject.html', subject=subject, teachers=teachers)

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    conn, cursor = get_db_conn()
    cursor.execute("DELETE FROM subjects WHERE subject_id=%s", (subject_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash('Subject deleted.', 'info')
    return redirect(url_for('manage_subject'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/fee_control')
def fee_control():
    q = request.args.get('q', '').strip()
    conn = None
    cursor = None
    student = None
    student_fees = None
    try:
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        
        if q:
            # Try to search by ID first if q is numeric
            search_id = None
            try:
                search_id = int(q)
            except ValueError:
                pass  # q is not a number, search by name instead
            
            if search_id:
                # Search by ID (numeric) - Only students enrolled in subjects
                cursor.execute(f"""
                    SELECT DISTINCT s.ID, s.Name, sd.Gender, sd.`Class`, sd.Phone
                    FROM `{TABLE_NAME_STUDENT}` s
                    LEFT JOIN `{TABLE_NAME_STUDENT_DATA}` sd ON s.ID = sd.ID
                    INNER JOIN student_subjects ss ON s.ID = ss.student_id
                    WHERE s.ID = %s
                    LIMIT 1
                """, (search_id,))
            else:
                # Search by name - Only students enrolled in subjects
                cursor.execute(f"""
                    SELECT DISTINCT s.ID, s.Name, sd.Gender, sd.`Class`, sd.Phone
                    FROM `{TABLE_NAME_STUDENT}` s
                    LEFT JOIN `{TABLE_NAME_STUDENT_DATA}` sd ON s.ID = sd.ID
                    INNER JOIN student_subjects ss ON s.ID = ss.student_id
                    WHERE s.Name LIKE %s
                    ORDER BY s.ID
                    LIMIT 1
                """, (f"%{q}%",))
            
            student = cursor.fetchone()
            
            if student:
                student_id = student['ID']
                # Get enrolled subjects and their fees for this student
                cursor.execute(f"""
                    SELECT 
                        COALESCE(f.fee_id, NULL) AS fee_id,
                        ss.student_id,
                        ss.subject_id,
                        COALESCE(f.amount, 65.00) AS amount,         -- default $65 when no fee record
                        COALESCE(f.paid, 0.00) AS paid,            -- default 0
                        COALESCE(f.status, 'pending') AS status,  -- default status
                        f.due_date,
                        sub.name AS subject_name,
                        t.Name AS teacher_name
                    FROM student_subjects ss
                    LEFT JOIN subjects sub ON ss.subject_id = sub.subject_id
                    LEFT JOIN `{TABLE_NAME_TEACHER}` t ON sub.teacher_id = t.ID
                    LEFT JOIN fees f ON f.student_id = ss.student_id AND f.subject_id = ss.subject_id
                    WHERE ss.student_id = %s
                    ORDER BY sub.name
                """, (student_id,))
                student_fees = cursor.fetchall()
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
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fees (student_id, subject_id, amount, due_date, status)
            VALUES (%s, %s, %s, %s, 'pending')
            ON DUPLICATE KEY UPDATE
                amount = VALUES(amount),
                due_date = VALUES(due_date),
                status = 'pending'
        """, (int(student_id), int(subject_id), float(amount) if amount else 0, due_date or None))
        conn.commit()
        flash('Fee added successfully.', 'success')
    except Exception as e:
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
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT student_id, amount, paid FROM fees WHERE fee_id=%s", (fee_id,))
        fee = cursor.fetchone()
        
        if not fee:
            flash('Fee not found.', 'error')
            return redirect(url_for('fee_control'))
        
        new_paid = float(fee['paid']) + float(amount_paid)
        new_status = 'paid' if new_paid >= float(fee['amount']) else 'partial'
        
        cursor.execute("""
            UPDATE fees SET paid=%s, status=%s WHERE fee_id=%s
        """, (new_paid, new_status, fee_id))
        conn.commit()
        flash('Payment recorded successfully.', 'success')
    except Exception as e:
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
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor(dictionary=True)
        
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
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('fee_control', q=student_id or ''))

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
        conn = mysql.connector.connect(**{**DB_CONF, "database": DB_NAME}, charset="utf8mb4")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO student_subjects (student_id, subject_id)
            VALUES (%s, %s)
        """, (int(student_id), int(subject_id)))
        conn.commit()
        flash('Student enrolled successfully.', 'success')
    except mysql.connector.IntegrityError:
        flash('Student already enrolled in this subject.', 'warning')
    except Exception as e:
        print('enroll_student error:', e)
        flash('Failed to enroll student: ' + str(e), 'error')
    finally:
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_subject'))

if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print("Failed to initialize database:", e)
        raise

    app.run(debug=True)
