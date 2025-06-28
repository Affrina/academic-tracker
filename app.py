from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
import math

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database config
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class Marks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    marks = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.String(20), nullable=False)

# Initialize DB
with app.app_context():
    db.create_all()

# Helper Functions
def calculate_grade_point(marks):
    if marks >= 90:
        return 10
    elif marks >= 80:
        return 9
    elif marks >= 70:
        return 8
    elif marks >= 60:
        return 7
    elif marks >= 50:
        return 6
    elif marks >= 40:
        return 5
    else:
        return 0

def get_grade_letter(marks):
    if marks >= 90:
        return 'A+'
    elif marks >= 80:
        return 'A'
    elif marks >= 70:
        return 'B'
    elif marks >= 60:
        return 'C'
    elif marks >= 50:
        return 'D'
    else:
        return 'F'

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect('/dashboard')
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/mark-entry', methods=['GET', 'POST'])
def mark_entry():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = db.session.get(User, user_id)

    if request.method == 'POST':
        semester = request.form['semester']
        num_subjects = int(request.form['numSubjects'])

        for i in range(1, num_subjects + 1):
            subject = request.form.get(f'subject{i}')
            marks = int(request.form.get(f'marks{i}'))

            new_mark = Marks(user_id=user_id, subject=subject, marks=marks, semester=semester)
            db.session.add(new_mark)

        db.session.commit()
        flash('Marks added successfully')
        return redirect(url_for('mark_entry'))

    semester_records = {}
    marks = Marks.query.filter_by(user_id=user_id).all()

    for mark in marks:
        mark.grade_point = round(mark.marks / 10, 2)
        mark.grade_letter = get_grade_letter(mark.marks)
        semester_records.setdefault(mark.semester, []).append(mark)

    cgpa_per_semester = {}
    for sem, records in semester_records.items():
        total_points = sum([record.grade_point for record in records])
        cgpa = round(total_points / len(records), 2)
        cgpa_per_semester[sem] = cgpa

    return render_template(
        'mark_entry.html',
        user=user,
        semester_records=semester_records,
        cgpa_per_semester=cgpa_per_semester
    )

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    marks = Marks.query.filter_by(user_id=user_id).all()

    # Semester-wise records
    semester_records = {}
    subject_data = []
    for mark in marks:
        mark.grade_point = calculate_grade_point(mark.marks)
        mark.grade_letter = get_grade_letter(mark.marks)
        semester_records.setdefault(mark.semester, []).append(mark)
        subject_data.append(mark.marks)

    # ✅ CGPA calculation per semester
    cgpa_per_semester = {}
    for sem, records in semester_records.items():
        total_points = sum([calculate_grade_point(m.marks) for m in records])
        cgpa = round(total_points / len(records), 2)
        cgpa_per_semester[sem] = cgpa

    # ✅ Strength & Weakness based on average marks
    subject_marks = {}
    for mark in marks:
        subject_marks.setdefault(mark.subject, []).append(mark.marks)

    strengths = {}
    weaknesses = {}
    for subject, mark_list in subject_marks.items():
        avg = round(sum(mark_list) / len(mark_list), 2)
        if avg >= 75:
            strengths[subject] = avg
        elif avg < 60:
            weaknesses[subject] = avg

    # ✅ Grade Distribution
    grade_distribution = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    for mark in marks:
        grade = get_grade_letter(mark.marks)
        grade_distribution[grade] += 1

    # ✅ Academic Health
    if subject_data:
        avg_marks = round(sum(subject_data) / len(subject_data), 2)
        variance = sum((x - avg_marks) ** 2 for x in subject_data) / len(subject_data)
        standard_deviation = round(math.sqrt(variance), 2)
    else:
        avg_marks = 0
        standard_deviation = 0

    return render_template(
        'dashboard.html',
        user=user,
        cgpa_per_semester=cgpa_per_semester,
        strengths=strengths,
        weaknesses=weaknesses,
        grade_distribution=grade_distribution,
        average_marks=avg_marks,
        standard_deviation=standard_deviation
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
