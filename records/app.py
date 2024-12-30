from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

# App configuration
app = Flask(__name__, static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/home/vintageLsd/student/static/uploads'
app.secret_key = 'your_secret_key'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    dob = db.Column(db.String(10), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    photo = db.Column(db.String(100))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    grade = db.Column(db.String(2), nullable=False)

# Initialize database
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def landing_page():
    return render_template('base.html')

@app.route('/home/vintageLsd/student/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/students', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        try:
            name = request.form['name']
            age = int(request.form['age'])
            dob = request.form['dob']
            gender = request.form['gender']


            photo = request.files.get('photo')
            photo_filename = ''
            if photo and photo.filename != '':
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_filename = filename


            new_student = Student(name=name, age=age, dob=dob, gender=gender, photo=photo_filename)
            db.session.add(new_student)
            db.session.commit()

            flash('Student added successfully!', 'success')
            return redirect(url_for('students_list'))
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')

    return render_template('add_student.html')

@app.route('/students/<int:id>/grades', methods=['GET'])
def view_grades(id):

    student = Student.query.get_or_404(id)


    grades = db.session.query(Grade, Course).join(Course, Grade.course_id == Course.id).filter(Grade.student_id == id).all()

    return render_template('view_grades.html', student=student, grades=grades)


@app.route('/students/list', methods=['GET'])
def students_list():
    students = Student.query.all()
    return render_template('students_list.html', students=students)


@app.route('/students/delete/<int:id>', methods=['POST'])
def delete_student(id):
    student = Student.query.get_or_404(id)


    Grade.query.filter_by(student_id=id).delete()


    Attendance.query.filter_by(student_id=id).delete()


    if student.photo:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], student.photo)
        if os.path.exists(photo_path):
            os.remove(photo_path)


    db.session.delete(student)
    db.session.commit()

    flash(f"Student with ID {id} deleted successfully!", 'success')
    return redirect(url_for('students_list'))


@app.route('/students/<int:id>', methods=['GET'])
def student_details(id):
    student = Student.query.get_or_404(id)

    # Fetch related data
    attendance = Attendance.query.filter_by(student_id=id).all()
    grades = Grade.query.filter_by(student_id=id).all()

    # Calculate CGPA
    grade_mapping = {'A': 4.0, 'B+': 3.5, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}
    total_points = sum([grade_mapping.get(grade.grade, 0) for grade in grades])
    total_courses = len(grades)
    cgpa = round(total_points / total_courses, 2) if total_courses > 0 else "N/A"


    courses = []
    for grade in grades:
        course = Course.query.get(grade.course_id)
        if course:
            courses.append({'name': course.name, 'credits': course.credits})

    return render_template(
        'student_details.html',
        student=student,
        attendance=attendance,
        grades=grades,
        cgpa=cgpa,
        courses=courses
    )
@app.route('/students/<int:id>/manage-courses', methods=['GET', 'POST'])
def manage_courses(id):
    student = Student.query.get_or_404(id)
    courses = Course.query.all()  # Fetch existing courses

    if request.method == 'POST':

        if 'register_course' in request.form:
            course_name = request.form.get('course_name')
            course_credits = request.form.get('course_credits')


            if course_name and course_credits.isdigit():
                new_course = Course(name=course_name, credits=int(course_credits))
                db.session.add(new_course)
                db.session.commit()
                flash("Course added successfully!", "success")
            else:
                flash("Invalid course name or credits.", "danger")


        elif 'save_grades' in request.form:
            selected_courses = request.form.getlist('courses')
            grades = request.form.getlist('grades')
            attendance_statuses = request.form.getlist('attendance')

            try:

                for course_id, grade, attendance_status in zip(selected_courses, grades, attendance_statuses):
                    grade_entry = Grade(student_id=id, course_id=course_id, grade=grade)
                    db.session.add(grade_entry)

                    attendance_entry = Attendance(student_id=id, date="2024-12-19", status=attendance_status)
                    db.session.add(attendance_entry)

                db.session.commit()
                flash("Grades and attendance registered successfully!", "success")
                return redirect(url_for('students_list'))
            except Exception as e:
                flash(f"Error: {e}", "danger")

    return render_template('manage_courses.html', student=student, courses=courses)


@app.route('/register-course', methods=['GET', 'POST'])
def register_course():
    if request.method == 'POST':
        course_name = request.form.get('course_name')
        course_credits = request.form.get('course_credits')


        if course_name and course_credits.isdigit():
            new_course = Course(name=course_name, credits=int(course_credits))
            db.session.add(new_course)
            db.session.commit()
            flash("Course added successfully!", "success")
        else:
            flash("Invalid course name or credits.", "danger")

    return render_template('register_course.html')

if __name__ == '__main__':
    app.run()

