from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "exam_readiness_secret"


# ---------- DATABASE CONNECTION ----------
def get_db():
    return sqlite3.connect("database.db")


# ---------- HOME PAGE ----------
@app.route("/")
def home():
    return render_template("index.html")


# ---------- STUDENT LOGIN ----------
@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        reg_no = request.form["reg_no"]
        password = request.form["password"]

        con = get_db()
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM students WHERE reg_no=? AND password=?",
            (reg_no, password)
        )
        student = cur.fetchone()
        con.close()

        if student:
            session["student_id"] = student[0]
            return redirect("/student_dashboard")
        else:
            return "Invalid Register Number or Password"

    return render_template("student_login.html")


# ---------- STUDENT DASHBOARD ----------
@app.route("/student_dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/student_login")

    sid = session["student_id"]

    con = get_db()
    cur = con.cursor()

    # student main data
    cur.execute("SELECT * FROM students WHERE id=?", (sid,))
    student = cur.fetchone()

    # subject wise assignment marks
    cur.execute(
        "SELECT subject_name, assignment_mark FROM subjects WHERE student_id=?",
        (sid,)
    )
    subjects = cur.fetchall()

    con.close()

    # values
    attendance = student[6]
    assignment = student[7]
    mock_test = student[8]
    syllabus = student[9]

    # readiness score calculation
    score = (
        assignment * 0.3 +
        attendance * 0.2 +
        mock_test * 0.3 +
        syllabus * 0.2
    )

    if score < 40:
        status = "Poor"
    elif score <= 60:
        status = "Average"
    elif score <= 80:
        status = "Good"
    else:
        status = "Excellent"

    return render_template(
        "student_dashboard.html",
        student=student,
        subjects=subjects,
        score=int(score),
        status=status
    )


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)