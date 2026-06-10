from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

import os
print("DB PATH:", os.path.abspath("database.db"))

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---------------- STUDENT LOGIN ----------------
@app.route("/student_login", methods=["GET","POST"])
def student_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Check in students table
        cursor.execute("SELECT reg_no, name, dept, year FROM students WHERE username=? AND password=?",
                       (username, password))
        student = cursor.fetchone()
        conn.close()

        if student:
            session["reg_no"] = student[0]
            session["student_name"] = student[1]
            
            session["department"] = student[2]
            session["year"] = student[3]
           
            return redirect("/student_dashboard")
        else:
            return render_template("student_login.html", error="Invalid Username or Password ❌")
    
    return render_template("student_login.html")


# -----------------------
# STUDENT DASHBOARD
# -----------------------
@app.route("/student_dashboard")
def student_dashboard():

    if "reg_no" not in session:
        return redirect("/student_login")

    reg_no = session.get("reg_no")
    student_name = session.get("student_name")
    dept = session.get("department")
    year = session.get("year")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 🔹 Subjects
    cursor.execute("""
        SELECT subject_name FROM subjects 
        WHERE dept=? AND year=?
    """, (dept, year))
    subjects = cursor.fetchall()

    # 🔹 Internal Marks
    cursor.execute("""
        SELECT subject, attendance, mock, assignment, unit_percent
        FROM internal_marks 
        WHERE reg_no=? AND dept=? AND year=?
    """, (reg_no, dept, year))

    marks = cursor.fetchall()

    # 🔹 CALCULATION
    total_internal = 0
    total_syllabus = 0
    subject_count = len(marks)

    for m in marks:
        total = m[1] + m[2] + m[3]
        total_internal += total
        total_syllabus += m[4]

    if subject_count > 0:
        avg_syllabus = round(total_syllabus / subject_count, 2)
        readiness_score = round(
            ((total_internal / (25 * subject_count)) * 70) +
            (avg_syllabus * 0.3), 2
        )
    else:
        avg_syllabus = 0
        readiness_score = 0

    # 🔥 STATUS (SUBJECT BASED)
    status = "Good"

    for m in marks:
        total = m[1] + m[2] + m[3]

        if total < 15:
            status = "Risk"
            break
        elif total < 20:
            status = "Medium"

    # 🔹 Study Planner Progress
    cursor.execute("SELECT COUNT(*) FROM study_planner WHERE student_id=?", (reg_no,))
    total_plans = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM study_planner
        WHERE student_id=? AND status='Completed'
    """, (reg_no,))
    completed_plans = cursor.fetchone()[0]

    planner_progress = int((completed_plans / total_plans) * 100) if total_plans > 0 else 0

    conn.close()

    return render_template("student_dashboard.html",
                           reg_no=reg_no,
                           student_name=student_name,
                           department=dept,
                           year=year,
                           marks=marks,
                           total_internal=total_internal,
                           syllabus_completion=avg_syllabus,
                           readiness_score=readiness_score,
                           status=status,
                           planner_progress=planner_progress,
                           subjects=subjects)

# -----------------------
# PREVIOUS YEAR PAPERS
# -----------------------
@app.route("/old_questions")
def old_questions():

    if "department" not in session:
        return redirect("/student_login")

    dept = session.get("department")
    semester = session.get("semester")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT subject, exam_type, file_name, semester, dept
        FROM question_papers
    """)

    papers = cursor.fetchall()
    conn.close()

    return render_template("old_questions.html", papers=papers)



# -----------------------
# STUDY PLANNER
# -----------------------
@app.route("/study_planner", methods=["GET","POST"])
def study_planner():

    if "reg_no" not in session:
        return redirect("/student_login")

    student_id = session["reg_no"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 🔹 Add Plan
    if request.method == "POST":

        subject = request.form["subject"]
        topic = request.form["topic"]
        study_date = request.form["study_date"]

        cursor.execute("""
            INSERT INTO study_planner 
            (student_id, subject, topic, study_date, status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (student_id, subject, topic, study_date))

        conn.commit()

    # 🔹 Get all plans
    cursor.execute("SELECT * FROM study_planner WHERE student_id=?", (student_id,))
    plans = cursor.fetchall()

    # 🔹 Today's date
    from datetime import date, datetime
    today = date.today().isoformat()

    # 🔹 Today's plans
    cursor.execute("""
        SELECT * FROM study_planner 
        WHERE student_id=? AND study_date=?
    """, (student_id, today))

    today_plans = cursor.fetchall()

    # 🔹 Progress calculation
    cursor.execute("SELECT COUNT(*) FROM study_planner WHERE student_id=?", (student_id,))
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM study_planner 
        WHERE student_id=? AND status='Completed'
    """, (student_id,))

    completed = cursor.fetchone()[0]

    progress = int((completed / total) * 100) if total > 0 else 0

    # 🔔 Overdue tasks
    cursor.execute("""
        SELECT COUNT(*) FROM study_planner
        WHERE student_id=? AND study_date < ? AND status='Pending'
    """,(student_id, today))

    overdue_count = cursor.fetchone()[0]

   
    conn.close()

    return render_template(
        "study_planner.html",
        plans=plans,
        today_plans=today_plans,
        progress=progress,
        today=today,
        overdue_count=overdue_count,

    )

#----------completed button--------
@app.route("/mark_completed/<int:plan_id>")
def mark_completed(plan_id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE study_planner
        SET status='Completed'
        WHERE id=?
    """, (plan_id,))

    conn.commit()
    conn.close()

    return redirect("/study_planner")

#---------delete button----------------

@app.route("/delete_plan/<int:plan_id>")
def delete_plan(plan_id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM study_planner WHERE id=?", (plan_id,))

    conn.commit()
    conn.close()

    return redirect("/study_planner")

    
# -----------------------
# START STUDY
# -----------------------
@app.route("/start_study")
def start_study():

    if "reg_no" not in session:
        return redirect("/student_login")

    student_id = session["reg_no"]

    from datetime import datetime,date
    now = datetime.now()
    today = date.today().isoformat()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Check if already running
    cursor.execute("""
    SELECT * FROM study_time
    WHERE student_id=? AND study_date=? AND end_time IS NULL
    """,(student_id,today))

    active = cursor.fetchone()

    if not active:
        cursor.execute("""
        INSERT INTO study_time (student_id,start_time,study_date)
        VALUES (?,?,?)
        """,(student_id, now, today))

        conn.commit()

    conn.close()

    return redirect("/time_overview")


# -----------------------
# STOP STUDY
# -----------------------
@app.route("/stop_study")
def stop_study():

    if "reg_no" not in session:
        return redirect("/student_login")

    student_id = session["reg_no"]

    from datetime import datetime,date
    now = datetime.now()
    today = date.today().isoformat()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE study_time
    SET end_time=?
    WHERE student_id=? AND study_date=? AND end_time IS NULL
    """,(now,student_id,today))

    conn.commit()
    conn.close()

    return redirect("/time_overview")


# -----------------------
# TIME OVERVIEW
# -----------------------
@app.route("/time_overview")
def time_overview():

    if "reg_no" not in session:
        return redirect("/student_login")

    student_id = session["reg_no"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    from datetime import date, datetime, timedelta

    today = date.today()

    # -------- TODAY TIME --------
    today_str = today.isoformat()

    cursor.execute("""
    SELECT start_time,end_time FROM study_time
    WHERE student_id=? AND study_date=?
    """,(student_id,today_str))

    rows = cursor.fetchall()

    total_seconds = 0

    for r in rows:
        start = datetime.fromisoformat(r[0])

        if r[1] is not None:
            end = datetime.fromisoformat(r[1])
        else:
            end = datetime.now()

        total_seconds += (end - start).total_seconds()

    today_hours = round(total_seconds/60,2)

    # -------- WEEK TOTAL --------
    week_start = today - timedelta(days=6)

    cursor.execute("""
    SELECT start_time,end_time FROM study_time
    WHERE student_id=? AND study_date >= ?
    """,(student_id,week_start.isoformat()))

    rows = cursor.fetchall()

    week_seconds = 0

    for r in rows:
        start = datetime.fromisoformat(r[0])

        if r[1] is not None:
            end = datetime.fromisoformat(r[1])
        else:
            end = datetime.now()

        week_seconds += (end - start).total_seconds()

    week_hours = round(week_seconds/3600,2)

    # -------- WEEK GRAPH --------
    labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    week_data = []

    start_of_week = today - timedelta(days=today.weekday())

    for i in range(7):

        day = start_of_week + timedelta(days=i)
        day_str = day.isoformat()

        cursor.execute("""
        SELECT start_time,end_time FROM study_time
        WHERE student_id=? AND study_date=?
        """,(student_id,day_str))

        day_rows = cursor.fetchall()

        seconds = 0

        for r in day_rows:
            start = datetime.fromisoformat(r[0])

            if r[1] is not None:
                end = datetime.fromisoformat(r[1])
            else:
                end = datetime.now()

            seconds += (end - start).total_seconds()

        hours = round(seconds/3600,2)
        week_data.append(hours)

    # -------- STREAK --------
    streak = 0
    check_day = today

    while True:

        day_str = check_day.isoformat()

        cursor.execute("""
        SELECT start_time,end_time FROM study_time
        WHERE student_id=? AND study_date=?
        """,(student_id, day_str))

        data = cursor.fetchall()

        if any(r[1] is not None for r in data):
            streak += 1
            check_day = check_day - timedelta(days=1)
        else:
            break

        
    goal = 20
    goal_percent = round((week_hours / goal) * 100, 2)

    conn.close()

   
    return render_template(
        "time_overview.html",
        today_hours=today_hours,
        week_hours=week_hours,
        goal=goal,
        goal_percent=goal_percent,
        labels=labels,
        week_data=week_data,
        streak=streak
    )


#-----------------students logout---------------
@app.route("/student_logout")
def student_logout():
    session.pop("student", None)
    return redirect("/")

# ---------------- FACULTY LOGIN ----------------
@app.route("/faculty_login", methods=["GET", "POST"])
def faculty_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM faculty WHERE username=? AND password=?",
            (username, password)
        )

        faculty = cursor.fetchone()
        conn.close()

        if faculty:
            session["faculty"] = username
            session["faculty_dept"]=faculty[2]
            return redirect("/faculty_dashboard")
        else:
            return render_template("faculty_login.html", error="Invalid Username or Password ❌")
       
    return render_template("faculty_login.html")
# ---------------- FACULTY DASHBOARD ----------------
@app.route("/faculty_dashboard")
def faculty_dashboard():
    return render_template("faculty_dashboard.html")

# ---------------- SELECT SUBJECT ----------------
@app.route("/select_subject", methods=["GET","POST"])
def select_subject():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # get subjects from database
    cursor.execute("SELECT subject_name FROM subjects")
    subjects = cursor.fetchall()

    conn.close()

    if request.method == "POST":
        session["dept"] = session["faculty_dept"]
        session["year"] = request.form["year"]
        session["semester"] = request.form["semester"]
        session["subject"] = request.form["subject"]
        session["regno"] = request.form["regno"]

        return redirect(url_for("internal_marks"))

    return render_template("select_subject.html", subjects=subjects)

# ---------------- INTERNAL MARKS PAGE ----------------
@app.route("/internal_marks")
def internal_marks():
    return render_template("internal_marks.html")



# ---------------- SAVE MARKS ----------------
@app.route("/save_marks", methods=["POST"])
def save_marks():
    assignment = request.form["assignment"]
    mock = request.form["mock"]
    attendance = request.form["attendance"]
    unit_percent = request.form["unit_percent"]
    total = request.form["total"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO internal_marks
        (dept,year,semester,subject,reg_no,
         assignment,mock,attendance,unit_percent,total)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        session["dept"],
        session["year"],
        session["semester"],
        session["subject"],
        session["regno"],
        assignment,
        mock,
        attendance,
        unit_percent,
        total
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("view_internal_marks"))

# ---------------- VIEW INTERNAL MARKS ----------------
@app.route("/view_internal_marks", methods=["GET", "POST"])
def view_internal_marks():

    if "faculty_dept" not in session:
        return redirect("/faculty_login")

    dept = session["faculty_dept"]   

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM internal_marks WHERE dept=?"
    params = [dept]

    if request.method == "POST":
        year = request.form.get("year")
        sem = request.form.get("semester")
        subject = request.form.get("subject")

        if year:
            query += " AND year=?"
            params.append(year)

        if sem:
            query += " AND semester=?"
            params.append(sem)

        if subject:
            query += " AND subject=?"
            params.append(subject)

    cur.execute(query, params)
    data = cur.fetchall()
    conn.close()

    return render_template("view_internal_marks.html", marks=data)


import pandas as pd
from flask import send_file

@app.route("/download_excel", methods=["POST"])
def download_excel():

    if "faculty_dept" not in session:
        return redirect("/faculty_login")

    dept = session["faculty_dept"]

    year = request.form.get("year")
    sem = request.form.get("semester")
    subject = request.form.get("subject")

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT reg_no, subject, assignment, mock, attendance, unit_percent, total
        FROM internal_marks
        WHERE dept=?
    """
    params = [dept]

    if year:
        query += " AND year=?"
        params.append(year)

    if sem:
        query += " AND semester=?"
        params.append(sem)

    if subject:
        query += " AND subject=?"
        params.append(subject)

    cur.execute(query, params)
    data = cur.fetchall()
    conn.close()

    
    df = pd.DataFrame(data, columns=[
        "Register No", "Subject", "Assignment", "Mock",
        "Attendance", "Unit %", "Total"
    ])

    # File name
    file_name = f"{subject}_{year}_Sem{sem}.xlsx"
    file_path = os.path.join("static", file_name)

    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

#-------------view students in faculty------
@app.route("/view_students", methods=["GET", "POST"])
def view_students():

    if "faculty_dept" not in session:
        return redirect("/faculty_login")

    dept = session["faculty_dept"]  
    print("Faculty dept:",dept)

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM students WHERE dept=?"
    params = [dept]

    if request.method == "POST":
        year = request.form.get("year")
        sem = request.form.get("semester")

        if year:
            query += " AND year=?"
            params.append(year)

        if sem:
            query += " AND semester=?"
            params.append(sem)

    cur.execute(query, params)
    students = cur.fetchall()
    conn.close()

    return render_template("view_students.html", students=students)


#---edit_mark
@app.route("/edit_marks/<reg_no>", methods=["GET","POST"])
def edit_marks(reg_no):

    if "faculty" not in session:
        return redirect("/faculty_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        subject = request.form["subject"]
        attendance = int(request.form["attendance"])
        mock = int(request.form["mock"])
        assignment = int(request.form["assignment"])
        unit_percent = int(request.form["unit_percent"])

        total = attendance + mock + assignment

        #  Get student dept/year/semester
        cursor.execute("""
            SELECT dept, year, semester 
            FROM students 
            WHERE reg_no=?
        """, (reg_no,))
        
        student = cursor.fetchone()

        dept = student[0]
        year = student[1]
        semester = student[2]

        # Check if subject already exists
        cursor.execute("""
            SELECT id FROM internal_marks 
            WHERE reg_no=? AND subject=?
        """, (reg_no, subject))

        existing = cursor.fetchone()

        if existing:
            # UPDATE
            cursor.execute("""
                UPDATE internal_marks
                SET attendance=?, mock=?, assignment=?, 
                    unit_percent=?, total=?
                WHERE reg_no=? AND subject=?
            """, (attendance, mock, assignment,
                  unit_percent, total, reg_no, subject))
        else:
            # INSERT
            cursor.execute("""
                INSERT INTO internal_marks
                (dept, year, semester, reg_no, subject, 
                 attendance, mock, assignment, unit_percent, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (dept, year, semester, reg_no, subject,
                  attendance, mock, assignment, unit_percent, total))

        conn.commit()
        conn.close()

        return redirect("/view_students")

    # GET METHOD
    cursor.execute("""
        SELECT subject, attendance, mock, assignment, unit_percent 
        FROM internal_marks WHERE reg_no=?
    """, (reg_no,))

    marks = cursor.fetchall()
    conn.close()

    return render_template("edit_marks.html",
                           reg_no=reg_no,
                           marks=marks)



#--------add student---------
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        reg_no = request.form["reg_no"]
        name = request.form["name"]
        dept = request.form["dept"]
        year = request.form["year"]
        semester = request.form["semester"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO students (reg_no, name, dept, year, semester)
            VALUES (?,?,?,?,?)
        """, (reg_no, name, dept, year, semester))
        conn.commit()
        conn.close()

        return redirect(url_for("view_students"))

    return render_template("add_student.html")


#----------------risk students-----------
from flask import request

@app.route("/risk_students")
def risk_students():
    dept = session["faculty_dept"]

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT s.reg_no, s.name, s.dept, i.total 
        FROM students s
        JOIN internal_marks i
        ON s.reg_no = i.reg_no
    """

    if dept:
        query += " WHERE s.dept = ?"
        cur.execute(query, (dept,))
    else:
        cur.execute(query)

    rows = cur.fetchall()
    conn.close()

    students = []
    for r in rows:
        if r["total"] < 15:
            risk = "High Risk"
        elif r["total"] < 20:
            risk = "Medium Risk"
        else:
            risk = "Safe"

        students.append({
            "reg_no": r["reg_no"],
            "name": r["name"],
            "dept": r["dept"],
            "total": r["total"],
            "risk": risk
        })

    return render_template("risk_students.html", students=students)

#------------staff upload question paper----------
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/papers"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/upload_paper", methods=["GET", "POST"])
def upload_paper():

    message = ""

    if request.method == "POST":

        dept = request.form["dept"]
        semester = request.form["semester"]
        print("uploaded dept:",dept)
        print("uploaded semester:",semester)
        subject = request.form["subject"]
        exam_type = request.form["exam_type"]
        file = request.files["file"]

        filename = secure_filename(file.filename)
        file.save(os.path.join("static/papers", filename))

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO question_papers (dept,semester , subject, exam_type, file_name)
        VALUES (?, ?, ?, ?, ?)
        """, (dept, semester, subject, exam_type, filename))

        conn.commit()
        conn.close()

        message = "Paper Uploaded Successfully ✅"

    return render_template("upload_paper.html", message=message)

#----------------- faculty logout------------------------
@app.route("/faculty_logout")
def faculty_logout():
    session.pop("faculty", None)
    return redirect("/")

#----------------admin login---------------------
@app.route("/admin_login", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = username
            return redirect("/admin_dashboard")

        else:
            return render_template("admin_login.html", error="Invalid Login ❌")

    return render_template("admin_login.html")

#----------------admin dashboard------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM faculty")
    faculty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM subjects")
    subjects = cursor.fetchone()[0]

   
    cursor.execute("""
    SELECT COUNT(DISTINCT reg_no) 
    FROM internal_marks 
    WHERE total < 13
    """)
    risk = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        students=students,
        faculty=faculty,
        subjects=subjects,
        risk=risk
    )

#-----------------manage_student-----------
@app.route("/manage_students", methods=["GET", "POST"])
def manage_students():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # ADD STUDENT
    if request.method == "POST":
        reg_no = request.form["reg_no"]
        name = request.form["name"]
        dept = request.form["dept"]
        year = request.form["year"]
        semester = request.form["semester"]
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute("""
        INSERT INTO students (reg_no, name, dept, year, semester, username, password)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (reg_no, name, dept, year, semester, username, password))

        conn.commit()

    # FETCH STUDENTS
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    conn.close()

    return render_template("manage_students.html", students=students)

#delete function
@app.route("/delete_student/<int:id>")
def delete_student(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/manage_students")
#-----------------manage faculty-------------
@app.route("/manage_faculty", methods=["GET", "POST"])
def manage_faculty():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # ADD FACULTY
    if request.method == "POST":
        name = request.form["name"]
        dept = request.form["dept"]
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute("""
        INSERT INTO faculty (name, dept, username, password)
        VALUES (?, ?, ?, ?)
        """, (name, dept, username, password))

        conn.commit()

    # FETCH
    cursor.execute("SELECT * FROM faculty")
    faculty = cursor.fetchall()

    conn.close()

    return render_template("manage_faculty.html", faculty=faculty)

#delete ----
@app.route("/delete_faculty/<int:id>")
def delete_faculty(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM faculty WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/manage_faculty")

#-------------------manage subject-------------
@app.route("/manage_subjects", methods=["GET", "POST"])
def manage_subjects():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # ADD SUBJECT
    if request.method == "POST":
        subject_name = request.form["subject_name"]
        dept = request.form["dept"]
        year = request.form["year"]
        semester = request.form["semester"]

        cursor.execute("""
        INSERT INTO subjects (subject_name, dept, year, semester)
        VALUES (?, ?, ?, ?)
        """, (subject_name, dept, year, semester))

        conn.commit()

    # FETCH SUBJECTS
    cursor.execute("SELECT * FROM subjects")
    subjects = cursor.fetchall()

    conn.close()

    return render_template("manage_subjects.html", subjects=subjects)

#delete
@app.route("/delete_subject/<int:id>")
def delete_subject(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM subjects WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/manage_subjects")

#------------admin high risk std-------------
@app.route("/admin_high_risk_students")
def admin_high_risk_students():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.name, s.reg_no, AVG(i.total) as avg_mark
    FROM internal_marks i
    JOIN students s ON s.reg_no = i.reg_no
    GROUP BY i.reg_no
    HAVING avg_mark < 13
    """)

    data = cursor.fetchall()
    conn.close()

    return render_template("admin_high_risk_students.html", data=data)


#-----------admin log out----------------
@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")
# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)