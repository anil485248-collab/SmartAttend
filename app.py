from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)

DATABASE = "smartattend.db"


# =========================================================
# PROGRAM-WISE ADMIN ACCESS CODES
# =========================================================

PROGRAM_CODES = {

    "B.Tech": "BT@2026",
    "M.Tech": "MT@2026",
    "Polytechnic / Diploma": "DIP@2026",
    "B.S.": "BS@2026",
    "Agriculture": "AGR@2026",

    "B.Pharmacy": "BPH@2026",
    "D.Pharmacy": "DPH@2026",
    "Nursing": "NUR@2026",
    "Ayurveda": "AYU@2026",

    "B.A.": "BA@2026",
    "B.Sc.": "BSC@2026",
    "B.Com.": "BCOM@2026"
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_database():

    connection = get_connection()

    cursor = connection.cursor()


    # =====================================================
    # TEACHERS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            teacher_id TEXT UNIQUE NOT NULL,

            name TEXT NOT NULL,

            mobile TEXT NOT NULL UNIQUE,

            category TEXT NOT NULL,

            program TEXT NOT NULL,

            password_hash TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

# =====================================================
    # ADMINS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)



    # =====================================================
    # STUDENTS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT UNIQUE,

            name TEXT NOT NULL,

            mobile TEXT NOT NULL UNIQUE,

            enrollment TEXT NOT NULL UNIQUE,

            category TEXT NOT NULL,

            program TEXT NOT NULL,

            branch TEXT,

            semester TEXT,

            password_hash TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # =====================================================
    # ATTENDANCE TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            attendance_date TEXT NOT NULL,

            status TEXT NOT NULL,

            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(student_id, attendance_date),

            FOREIGN KEY(student_id)
            REFERENCES students(student_id)
        )
    """)

    # =====================================================
    # COLLEGE LOCATION TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS college_location (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            latitude REAL NOT NULL,

            longitude REAL NOT NULL,

            radius REAL NOT NULL DEFAULT 50,

            required_minutes INTEGER NOT NULL DEFAULT 60,

            max_accuracy REAL NOT NULL DEFAULT 30,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    connection.commit()

# =====================================================
    # DEFAULT ADMIN ACCOUNT
    # =====================================================

    cursor.execute("""
        SELECT admin_id
        FROM admins
        LIMIT 1
    """)

    existing_admin = cursor.fetchone()

    if not existing_admin:

        admin_password = generate_password_hash(
            "Admin@2026"
        )

        cursor.execute("""
            INSERT INTO admins
            (admin_id, name, password_hash)
            VALUES (?, ?, ?)
        """, (
            "ADM-000001",
            "System Admin",
            admin_password
        ))

    connection.close()

# =====================================================
# COLLEGE LOCATION API
# =====================================================

@app.route("/api/admin/location", methods=["GET", "POST"])
def college_location():

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        data = request.get_json()

        if not data:
            connection.close()
            return jsonify({
                "success": False,
                "message": "No location data received."
            }), 400

        latitude = data.get("latitude")
        longitude = data.get("longitude")
        radius = data.get("radius", 50)
        required_minutes = data.get("required_minutes", 60)
        max_accuracy = data.get("max_accuracy", 30)

        if latitude is None or longitude is None:
            connection.close()
            return jsonify({
                "success": False,
                "message": "Latitude and longitude are required."
            }), 400

        cursor.execute("DELETE FROM college_location")

        cursor.execute("""
            INSERT INTO college_location
            (
                latitude,
                longitude,
                radius,
                required_minutes,
                max_accuracy
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            float(latitude),
            float(longitude),
            float(radius),
            int(required_minutes),
            float(max_accuracy)
        ))

        connection.commit()
        connection.close()

        return jsonify({
            "success": True,
            "message": "College location saved successfully."
        }), 200

    cursor.execute("""
        SELECT
            latitude,
            longitude,
            radius,
            required_minutes,
            max_accuracy
        FROM college_location
        ORDER BY id DESC
        LIMIT 1
    """)

    location = cursor.fetchone()
    connection.close()

    if not location:
        return jsonify({
            "success": False,
            "message": "College location is not configured by Admin."
        }), 404

    return jsonify({
        "success": True,
        "location": {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "radius": location["radius"],
            "required_minutes": location["required_minutes"],
            "max_accuracy": location["max_accuracy"]
        }
    }), 200

# =========================================================
# CORS
# =========================================================

@app.after_request
def add_cors_headers(response):

    response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

    return response


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return "SmartAttend Backend is Running!"


# =========================================================
# STATUS
# =========================================================

@app.route("/api/status")
def status():

    return jsonify({

        "status": "success",

        "message": "SmartAttend Database Backend is Running"

    })


# =========================================================
# TEACHER REGISTRATION
# =========================================================

@app.route("/api/teachers/register", methods=["POST"])
def register_teacher():

    data = request.get_json()


    if not data:

        return jsonify({

            "success": False,

            "message": "No registration data received."

        }), 400


    name = data.get("name", "").strip()

    mobile = data.get("mobile", "").strip()

    category = data.get("category", "").strip()

    program = data.get("program", "").strip()

    access_code = data.get("access_code", "").strip()

    password = data.get("password", "")


    if not all([
        name,
        mobile,
        category,
        program,
        access_code,
        password
    ]):

        return jsonify({

            "success": False,

            "message": "Please fill all required fields."

        }), 400


    if program not in PROGRAM_CODES:

        return jsonify({

            "success": False,

            "message": "Invalid program selected."

        }), 400


    if PROGRAM_CODES[program] != access_code:

        return jsonify({

            "success": False,

            "message": "Invalid Admin Access Code for this program."

        }), 403


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        "SELECT teacher_id FROM teachers WHERE mobile = ?",
        (mobile,)
    )

    existing_teacher = cursor.fetchone()


    if existing_teacher:

        connection.close()

        return jsonify({

            "success": False,

            "message": "A teacher with this mobile number is already registered."

        }), 409


    cursor.execute(
        "SELECT COUNT(*) AS total FROM teachers"
    )

    total_teachers = cursor.fetchone()["total"]

    teacher_id = f"TCH-{total_teachers + 1:06d}"


    password_hash = generate_password_hash(password)


    cursor.execute("""
        INSERT INTO teachers
        (
            teacher_id,
            name,
            mobile,
            category,
            program,
            password_hash
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (

        teacher_id,
        name,
        mobile,
        category,
        program,
        password_hash

    ))


    connection.commit()

    connection.close()


    return jsonify({

        "success": True,

        "message": "Teacher registered successfully.",

        "teacher_id": teacher_id,

        "name": name,

        "program": program

    }), 201


# =========================================================
# STUDENT REGISTRATION
# =========================================================

@app.route("/api/students/register", methods=["POST"])
def register_student():

    data = request.get_json()


    if not data:

        return jsonify({

            "success": False,

            "message": "No registration data received."

        }), 400


    name = data.get("name", "").strip()

    mobile = data.get("mobile", "").strip()

    enrollment = data.get("enrollment", "").strip()

    category = data.get("category", "").strip()

    program = data.get("program", "").strip()

    branch = data.get("branch", "").strip()

    semester = str(
        data.get("semester", "")
    ).strip()

    password = data.get("password", "")


    if not all([
        name,
        mobile,
        enrollment,
        category,
        program,
        password
    ]):

        return jsonify({

            "success": False,

            "message": "Please fill all required fields."

        }), 400


    if not mobile.isdigit() or len(mobile) != 10:

        return jsonify({

            "success": False,

            "message": "Please enter a valid 10-digit mobile number."

        }), 400


    if len(password) < 8:

        return jsonify({

            "success": False,

            "message": "Password must contain at least 8 characters."

        }), 400


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        "SELECT student_id FROM students WHERE mobile = ?",
        (mobile,)
    )

    existing_mobile = cursor.fetchone()


    if existing_mobile:

        connection.close()

        return jsonify({

            "success": False,

            "message": "A student with this mobile number is already registered."

        }), 409


    cursor.execute(
        "SELECT student_id FROM students WHERE enrollment = ?",
        (enrollment,)
    )

    existing_enrollment = cursor.fetchone()


    if existing_enrollment:

        connection.close()

        return jsonify({

            "success": False,

            "message": "This enrollment number is already registered."

        }), 409


    cursor.execute(
        "SELECT COUNT(*) AS total FROM students"
    )

    total_students = cursor.fetchone()["total"]

    student_id = f"STU-{total_students + 1:06d}"


    password_hash = generate_password_hash(password)


    cursor.execute("""
        INSERT INTO students
        (
            student_id,
            name,
            mobile,
            enrollment,
            category,
            program,
            branch,
            semester,
            password_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        student_id,
        name,
        mobile,
        enrollment,
        category,
        program,
        branch,
        semester,
        password_hash

    ))


    connection.commit()

    connection.close()


    return jsonify({

        "success": True,

        "message": "Student registered successfully.",

        "student_id": student_id,

        "name": name,

        "program": program,

        "branch": branch,

        "semester": semester

    }), 201


# =========================================================
# STUDENT LOGIN
# =========================================================

@app.route("/api/students/login", methods=["POST"])
def login_student():

    data = request.get_json()


    if not data:

        return jsonify({

            "success": False,

            "message": "No login data received."

        }), 400


    student_id = data.get("student_id", "").strip()

    password = data.get("password", "")


    if not student_id or not password:

        return jsonify({

            "success": False,

            "message": "Please enter Student ID and Password."

        }), 400


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            student_id,
            name,
            mobile,
            enrollment,
            category,
            program,
            branch,
            semester,
            password_hash
        FROM students
        WHERE student_id = ?
    """, (student_id,))


    student = cursor.fetchone()

    connection.close()


    if not student:

        return jsonify({

            "success": False,

            "message": "Invalid Student ID or Password."

        }), 401


    if not check_password_hash(
        student["password_hash"],
        password
    ):

        return jsonify({

            "success": False,

            "message": "Invalid Student ID or Password."

        }), 401


    return jsonify({

        "success": True,

        "message": "Student login successful.",

        "student": {

            "student_id": student["student_id"],

            "name": student["name"],

            "mobile": student["mobile"],

            "enrollment": student["enrollment"],

            "category": student["category"],

            "program": student["program"],

            "branch": student["branch"],

            "semester": student["semester"]

        }

    }), 200


# =========================================================
# MARK ATTENDANCE
# =========================================================

@app.route("/api/attendance/mark", methods=["POST"])
def mark_attendance():

    data = request.get_json()


    if not data:

        return jsonify({

            "success": False,

            "message": "No attendance data received."

        }), 400


    student_id = data.get("student_id", "").strip()

    attendance_date = data.get(
        "attendance_date",
        str(date.today())
    ).strip()

    status_value = data.get("status", "").strip().capitalize()


    if not student_id or not status_value:

        return jsonify({

            "success": False,

            "message": "Student ID and attendance status are required."

        }), 400


    if status_value not in ["Present", "Absent"]:

        return jsonify({

            "success": False,

            "message": "Attendance status must be Present or Absent."

        }), 400


    connection = get_connection()

    cursor = connection.cursor()


    # Check student exists

    cursor.execute(
        "SELECT student_id FROM students WHERE student_id = ?",
        (student_id,)
    )

    student = cursor.fetchone()


    if not student:

        connection.close()

        return jsonify({

            "success": False,

            "message": "Student not found."

        }), 404


    # Save / update attendance

    cursor.execute("""
        INSERT INTO attendance
        (
            student_id,
            attendance_date,
            status
        )
        VALUES (?, ?, ?)

        ON CONFLICT(student_id, attendance_date)

        DO UPDATE SET
            status = excluded.status
    """, (

        student_id,
        attendance_date,
        status_value

    ))


    connection.commit()

    connection.close()


    return jsonify({

        "success": True,

        "message": "Attendance saved successfully.",

        "student_id": student_id,

        "date": attendance_date,

        "status": status_value

    }), 200


# =========================================================
# GET STUDENT ATTENDANCE
# =========================================================

@app.route("/api/students/<student_id>/attendance", methods=["GET"])
def get_student_attendance(student_id):

    connection = get_connection()

    cursor = connection.cursor()


    # Check student

    cursor.execute("""
        SELECT
            student_id,
            name,
            program,
            branch,
            semester
        FROM students
        WHERE student_id = ?
    """, (student_id,))


    student = cursor.fetchone()


    if not student:

        connection.close()

        return jsonify({

            "success": False,

            "message": "Student not found."

        }), 404


    # Attendance records

    cursor.execute("""
        SELECT
            attendance_date,
            status,
            marked_at
        FROM attendance
        WHERE student_id = ?
        ORDER BY attendance_date DESC
    """, (student_id,))


    records = cursor.fetchall()


    # Calculate attendance

    total_days = len(records)

    present_days = sum(
        1
        for record in records
        if record["status"] == "Present"
    )

    absent_days = sum(
        1
        for record in records
        if record["status"] == "Absent"
    )


    if total_days > 0:

        attendance_percentage = round(
            (present_days / total_days) * 100,
            2
        )

    else:

        attendance_percentage = 0


    attendance_history = []


    for record in records:

        attendance_history.append({

            "date": record["attendance_date"],

            "status": record["status"],

            "marked_at": record["marked_at"]

        })


    connection.close()


    return jsonify({

        "success": True,

        "student": {

            "student_id": student["student_id"],

            "name": student["name"],

            "program": student["program"],

            "branch": student["branch"],

            "semester": student["semester"]

        },

        "summary": {

            "present_days": present_days,

            "absent_days": absent_days,

            "total_days": total_days,

            "attendance_percentage": attendance_percentage

        },

        "history": attendance_history

    }), 200


# =========================================================
# TEACHER LOGIN
# =========================================================

@app.route("/api/teachers/login", methods=["POST"])
def login_teacher():

    data = request.get_json()


    if not data:

        return jsonify({

            "success": False,

            "message": "No login data received."

        }), 400


    teacher_id = data.get("teacher_id", "").strip()

    password = data.get("password", "")


    if not teacher_id or not password:

        return jsonify({

            "success": False,

            "message": "Please enter Teacher ID and Password."

        }), 400


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            teacher_id,
            name,
            mobile,
            category,
            program,
            password_hash
        FROM teachers
        WHERE teacher_id = ?
    """, (teacher_id,))


    teacher = cursor.fetchone()

    connection.close()


    if not teacher:

        return jsonify({

            "success": False,

            "message": "Invalid Teacher ID or Password."

        }), 401


    if not check_password_hash(
        teacher["password_hash"],
        password
    ):

        return jsonify({

            "success": False,

            "message": "Invalid Teacher ID or Password."

        }), 401


    return jsonify({

        "success": True,

        "message": "Teacher login successful.",

        "teacher": {

            "teacher_id": teacher["teacher_id"],

            "name": teacher["name"],

            "mobile": teacher["mobile"],

            "category": teacher["category"],

            "program": teacher["program"]

        }

    }), 200


# =========================================================
# START SERVER
# =========================================================
@app.route("/api/admin/login", methods=["POST"])
def login_admin():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No login data received."
        }), 400

    admin_id = data.get("admin_id", "").strip()
    password = data.get("password", "")

    if not admin_id or not password:
        return jsonify({
            "success": False,
            "message": "Please enter Admin ID and Password."
        }), 400

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            admin_id,
            name,
            password_hash
        FROM admins
        WHERE admin_id = ?
    """, (admin_id,))

    admin = cursor.fetchone()

    connection.close()

    if not admin:
        return jsonify({
            "success": False,
            "message": "Invalid Admin ID or Password."
        }), 401

    if not check_password_hash(
        admin["password_hash"],
        password
    ):
        return jsonify({
            "success": False,
            "message": "Invalid Admin ID or Password."
        }), 401

    return jsonify({
        "success": True,
        "message": "Admin login successful.",
        "admin": {
            "admin_id": admin["admin_id"],
            "name": admin["name"]
        }
    }), 200

@app.route("/api/admin/students", methods=["GET"])
def get_all_students():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            mobile,
            enrollment,
            category,
            program,
            branch,
            semester
        FROM students
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

    result = []

    for student in students:

        cursor.execute("""
            SELECT
                COUNT(*) AS total_days,
                SUM(
                    CASE
                        WHEN status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                ) AS present_days
            FROM attendance
            WHERE student_id = ?
        """, (student["student_id"],))

        attendance_data = cursor.fetchone()

        total_days = attendance_data["total_days"] or 0
        present_days = attendance_data["present_days"] or 0

        if total_days > 0:
            attendance_percentage = round(
                (present_days / total_days) * 100,
                2
            )
        else:
            attendance_percentage = 0

        result.append({

            "student_id": student["student_id"],

            "name": student["name"],

            "mobile": student["mobile"],

            "enrollment": student["enrollment"],

            "category": student["category"],

            "program": student["program"],

            "branch": student["branch"] or "N/A",

            "semester": student["semester"] or "N/A",

            "total_days": total_days,

            "present_days": present_days,

            "attendance_percentage":
                attendance_percentage

        })

    connection.close()

    return jsonify({

        "success": True,

        "total_students": len(result),

        "students": result

    }), 200

@app.route("/admin-dashboard.html")
def admin_dashboard_page():
    return send_from_directory(".", "admin-dashboard.html")

@app.route("/admin-students.html")
def admin_students_page():
    return send_from_directory(".", "admin-students.html")

@app.route("/admin-attendance.html")
def admin_attendance_page():
    return send_from_directory(".", "admin-attendance.html")

@app.route("/admin-location.html")
def admin_location_page():
    return send_from_directory(".", "admin-location.html")
@app.route("/admin-settings.html")
def admin_settings_page():
    return send_from_directory(".", "admin-settings.html")

@app.route("/student-dashboard.html")
def student_dashboard_page():
    return send_from_directory(".", "student-dashboard.html")

@app.route("/student-login.html")
def student_login_page():
    return send_from_directory(".", "student-login.html")

@app.route("/student-register.html")
def student_register_page():
    return send_from_directory(".", "student-register.html")

@app.route("/student.html")
def student_page():
    return send_from_directory(".", "student.html")

@app.route("/teacher.html")
def teacher_page():
    return send_from_directory(".", "teacher.html")

@app.route("/index.html")
def index_page():
    return send_from_directory(".", "index.html")

@app.route("/admin.html")
def admin_page():
    return send_from_directory(".", "admin.html")

# Teachers API

@app.route("/admin-teachers.html")
def admin_teachers_page():
    return send_from_directory(".", "admin-teachers.html")

@app.route("/api/admin/teachers", methods=["GET"])
def get_all_teachers():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            teacher_id,
            name,
            mobile,
            category,
            program,
            created_at
        FROM teachers
        ORDER BY id DESC
    """)

    teachers = cursor.fetchall()

    result = []

    for teacher in teachers:

        result.append({
            "teacher_id": teacher["teacher_id"],
            "name": teacher["name"],
            "mobile": teacher["mobile"],
            "category": teacher["category"],
            "program": teacher["program"],
            "created_at": teacher["created_at"]
        })

    connection.close()

    return jsonify({
        "success": True,
        "total_teachers": len(result),
        "teachers": result
    }), 200

# ============================================================
# AUDIT LOGS API
# ============================================================

@app.route("/api/admin/audit-logs", methods=["GET"])
def get_audit_logs():

    connection = get_connection()
    cursor = connection.cursor()

    # Create audit_logs table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()

    cursor.execute("""
        SELECT
            id,
            action,
            description,
            created_at
        FROM audit_logs
        ORDER BY id DESC
    """)

    logs = cursor.fetchall()

    result = []

    for log in logs:

        result.append({
            "id": log["id"],
            "action": log["action"],
            "description": log["description"],
            "created_at": log["created_at"]
        })

    connection.close()

    return jsonify({
        "success": True,
        "total_logs": len(result),
        "logs": result
    }), 200

@app.route("/admin-audit-logs.html")
def admin_audit_logs_page():
    return send_from_directory(".", "admin-audit-logs.html")

@app.route("/teacher-register.html")
def teacher_register_page():
    return send_from_directory(".", "teacher-register.html")

@app.route("/teacher-login.html")
def teacher_login_page():
    return send_from_directory(".", "teacher-login.html")

@app.route("/teacher-dashboard.html")
def teacher_dashboard_page():
    return send_from_directory(".", "teacher-dashboard.html")

@app.route("/api/admin/students/<student_id>", methods=["DELETE"])
def delete_student(student_id):
    student_id = student_id.strip()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Student check
        cursor.execute("""
            SELECT name, program
            FROM students
            WHERE student_id = ?
        """, (student_id,))

        student = cursor.fetchone()

        if not student:
            connection.close()
            return jsonify({
                "success": False,
                "message": "Student not found."
            }), 404

        student_name = student["name"]
        student_program = student["program"]

        # Attendance records delete
        cursor.execute("""
            DELETE FROM attendance
            WHERE student_id = ?
        """, (student_id,))

        # Student delete
        cursor.execute("""
            DELETE FROM students
            WHERE student_id = ?
        """, (student_id,))

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (action, description)
            VALUES (?, ?)
        """, (
            "DELETE STUDENT",
            f"Student {student_id} ({student_name}) from {student_program} was deleted by Admin."
        ))

        connection.commit()
        connection.close()

        return jsonify({
            "success": True,
            "message": f"Student {student_id} deleted successfully."
        }), 200

    except Exception as error:
        connection.rollback()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Unable to delete student.",
            "error": str(error)
        }), 500


@app.route("/api/admin/teachers/<teacher_id>", methods=["DELETE"])
def delete_teacher(teacher_id):
    teacher_id = teacher_id.strip()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Teacher check
        cursor.execute("""
            SELECT name, program
            FROM teachers
            WHERE teacher_id = ?
        """, (teacher_id,))

        teacher = cursor.fetchone()

        if not teacher:
            connection.close()
            return jsonify({
                "success": False,
                "message": "Teacher not found."
            }), 404

        teacher_name = teacher["name"]
        teacher_program = teacher["program"]

        # Teacher delete
        cursor.execute("""
            DELETE FROM teachers
            WHERE teacher_id = ?
        """, (teacher_id,))

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs (action, description)
            VALUES (?, ?)
        """, (
            "DELETE TEACHER",
            f"Teacher {teacher_id} ({teacher_name}) from {teacher_program} was deleted by Admin."
        ))

        connection.commit()
        connection.close()

        return jsonify({
            "success": True,
            "message": f"Teacher {teacher_id} deleted successfully."
        }), 200

    except Exception as error:
        connection.rollback()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Unable to delete teacher.",
            "error": str(error)
        }), 500

@app.route("/api/teacher/students", methods=["GET"])
def get_teacher_students():
    teacher_id = request.args.get("teacher_id", "").strip()
    semester = request.args.get("semester", "").strip()
    branch = request.args.get("branch", "").strip()

    if not teacher_id or not semester or not branch:
        return jsonify({
            "success": False,
            "message": "Teacher ID and semester are required and branch."
        }), 400

    connection = get_connection()
    cursor = connection.cursor()

    # Get teacher's authorized program
    cursor.execute("""
        SELECT program
        FROM teachers
        WHERE teacher_id = ?
    """, (teacher_id,))

    teacher = cursor.fetchone()

    if not teacher:
        connection.close()
        return jsonify({
            "success": False,
            "message": "Teacher not found."
        }), 404

    program = teacher["program"]

    # Get only students from teacher's program and selected semester
    cursor.execute("""
        SELECT student_id, name, enrollment, program, branch, semester, mobile
        FROM students
        WHERE program = ?
        AND semester = ?
        AND branch = ?
        ORDER BY name
    """, (program, semester, branch))

    students = cursor.fetchall()
    connection.close()

    result = []

    for student in students:
        result.append({
            "student_id": student["student_id"],
            "name": student["name"],
            "enrollment": student["enrollment"],
            "program": student["program"],
            "branch": student["branch"],
            "semester": student["semester"],
            "mobile": student["mobile"]
        })

    return jsonify({
        "success": True,
        "program": program,
        "semester": semester,
        "total_students": len(result),
        "students": result
    }), 200

@app.route("/admin.html")
def admin_page():
    return send_from_directory(".", "admin.html")


init_database()


init_database()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        ssl_context=("localhost+3.pem", "localhost+3-key.pem")
    )
