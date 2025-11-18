from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['DATABASE'] = 'hospital.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database initialization
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    print('conn cursor created')
    
    # Users table (for authentication)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Departments table
    c.execute('''CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        doctors_count INTEGER DEFAULT 0
    )''')
    
    # Doctors table
    c.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        department_id INTEGER,
        phone TEXT,
        email TEXT,
        experience INTEGER,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )''')
    
    # Doctor availability table
    c.execute('''CREATE TABLE IF NOT EXISTS doctor_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        is_available INTEGER DEFAULT 1,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )''')
    
    # Patients table
    c.execute('''CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        blood_group TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Appointments table
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT DEFAULT 'Booked',
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )''')
    
    # Treatments table
    c.execute('''CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER,
        diagnosis TEXT,
        prescription TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id)
    )''')
    
    # Create default admin if not exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_password = ('admin123')
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                 ('admin', admin_password, 'admin'))
    
    # Insert sample departments
    departments = [
        ('Pulmonology','Lungs'),
        ('Cardiology', 'Heart and cardiovascular system'),
        ('Neurology', 'Brain and nervous system'),
        ('Orthopedics', 'Bones and muscles'),
        ('Pediatrics', 'Children health'),
        ('Dermatology', 'Skin conditions'),
        ('General Medicine', 'General health issues')
    ]
    
    for dept in departments:
        c.execute("INSERT OR IGNORE INTO departments (name, description) VALUES (?, ?)", dept)
    
    conn.commit()
    conn.close()
    print('cursor committed and closed ')

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

# Role-based access decorator
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Access denied!', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Helper function to get database connection
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        conn = get_db()
        user_data = conn.execute("SELECT * FROM users WHERE username = ? AND role = ?", 
                                (username, role)).fetchone()
        conn.close()
        
        if user_data and (user_data['password']==password):
            user = User(user_data['id'], user_data['username'], user_data['role'])
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        blood_group = request.form.get('blood_group')
        
        conn = get_db()
        
        # Check if username exists
        existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash('Username already exists!', 'danger')
            conn.close()
            return redirect(url_for('register'))
        
        # Create user
        hashed_password = (password)
        conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, hashed_password, 'patient'))
        
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # Create patient profile
        conn.execute("""INSERT INTO patients (user_id, name, age, gender, phone, email, address, blood_group)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, name, age, gender, phone, email, address, blood_group))
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    
    if current_user.role == 'admin':
        total_doctors = conn.execute("SELECT COUNT(*) as count FROM doctors WHERE is_active = 1").fetchone()['count']
        total_patients = conn.execute("SELECT COUNT(*) as count FROM patients WHERE is_active = 1").fetchone()['count']
        total_appointments = conn.execute("SELECT COUNT(*) as count FROM appointments").fetchone()['count']
        
        recent_appointments = conn.execute("""
            SELECT a.*, p.name as patient_name, d.name as doctor_name, d.specialization
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            ORDER BY a.created_at DESC LIMIT 10
        """).fetchall()
        
        conn.close()
        
        return render_template('admin_dashboard.html', 
                             total_doctors=total_doctors,
                             total_patients=total_patients,
                             total_appointments=total_appointments,
                             recent_appointments=recent_appointments)
    
    elif current_user.role == 'doctor':
        doctor = conn.execute("SELECT * FROM doctors WHERE user_id = ?", (current_user.id,)).fetchone()
        
        today = datetime.now().strftime('%Y-%m-%d')
        upcoming_appointments = conn.execute("""
            SELECT a.*, p.name as patient_name, p.phone, p.age, p.gender
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.doctor_id = ? AND a.date >= ? AND a.status = 'Booked'
            ORDER BY a.date, a.time
        """, (doctor['id'], today)).fetchall()
        
        total_patients = conn.execute("""
            SELECT COUNT(DISTINCT patient_id) as count FROM appointments WHERE doctor_id = ?
        """, (doctor['id'],)).fetchone()['count']
        
        conn.close()
        
        return render_template('doctor_dashboard.html',
                             doctor=doctor,
                             upcoming_appointments=upcoming_appointments,
                             total_patients=total_patients)
    
    elif current_user.role == 'patient':
        patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (current_user.id,)).fetchone()
        
        departments = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()
        
        today = datetime.now().strftime('%Y-%m-%d')
        upcoming_appointments = conn.execute("""
            SELECT a.*, d.name as doctor_name, d.specialization
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.patient_id = ? AND a.date >= ?
            ORDER BY a.date, a.time
        """, (patient['id'], today)).fetchall()
        
        past_appointments = conn.execute("""
            SELECT a.*, d.name as doctor_name, d.specialization, t.diagnosis, t.prescription
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            LEFT JOIN treatments t ON a.id = t.appointment_id
            WHERE a.patient_id = ? AND (a.date < ? OR a.status = 'Completed')
            ORDER BY a.date DESC, a.time DESC
        """, (patient['id'], today)).fetchall()
        
        conn.close()
        
        return render_template('patient_dashboard.html',
                             patient=patient,
                             departments=departments,
                             upcoming_appointments=upcoming_appointments,
                             past_appointments=past_appointments)
    
    conn.close()
    return redirect(url_for('login'))

# Admin routes
@app.route('/admin/doctors', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def manage_doctors():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            name = request.form.get('name')
            specialization = request.form.get('specialization')
            department_id = request.form.get('department_id')
            phone = request.form.get('phone')
            email = request.form.get('email')
            experience = request.form.get('experience')
            
            # Check if username exists
            existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                flash('Username already exists!', 'danger')
            else:
                hashed_password = (password)
                conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                           (username, hashed_password, 'doctor'))
                
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                phone_no=request.form['phone']
                if len(phone)!=10:
                    flash('Phone Number should be 10 digits','danger')
                conn.execute("""INSERT INTO doctors (user_id, name, specialization, department_id, phone, email, experience)
                              VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (user_id, name, specialization, department_id, phone, email, experience))
                
                conn.execute("UPDATE departments SET doctors_count = doctors_count + 1 WHERE id = ?", (department_id,))
                conn.commit()
                flash('Doctor added successfully!', 'success')
        
        elif action == 'delete':
            doctor_id = request.form.get('doctor_id')
            doctor = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
            conn.execute("UPDATE doctors SET is_active = 0 WHERE id = ?", (doctor_id,))
            conn.execute("UPDATE departments SET doctors_count = doctors_count - 1 WHERE id = ?", (doctor['department_id'],))
            conn.execute('DELETE from doctors where id=?',(doctor_id))
            conn.execute('DELETE from users where id=?',(doctor['user_id'],))
            conn.commit()
            flash('Doctor removed successfully!', 'success')
    
    doctors = conn.execute("""
        SELECT d.*, dep.name as department_name
        FROM doctors d
        LEFT JOIN departments dep ON d.department_id = dep.id
        WHERE d.is_active = 1
        ORDER BY d.name
    """).fetchall()
    
    departments = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()
    
    conn.close()
    
    return render_template('admin_doctors.html', doctors=doctors, departments=departments)

@app.route('/admin/patients')
@login_required
@role_required(['admin'])
def manage_patients():
    conn = get_db()
    
    search = request.args.get('search', '')
    if search:
        patients = conn.execute("""
            SELECT * FROM patients 
            WHERE is_active = 1 AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)
            ORDER BY name
        """, (f'%{search}%', f'%{search}%', f'%{search}%')).fetchall()
    else:
        patients = conn.execute("SELECT * FROM patients WHERE is_active = 1 ORDER BY name").fetchall()
    
    conn.close()
    
    return render_template('admin_patients.html', patients=patients, search=search)

@app.route('/admin/appointments')
@login_required
@role_required(['admin'])
def manage_appointments():
    conn = get_db()
    
    appointments = conn.execute("""
        SELECT a.*, p.name as patient_name, d.name as doctor_name, d.specialization
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.date DESC, a.time DESC
    """).fetchall()
    
    conn.close()
    
    return render_template('admin_appointments.html', appointments=appointments)

# Doctor routes
@app.route('/doctor/appointments')
@login_required
@role_required(['doctor'])
def doctor_appointments():
    conn = get_db()
    
    doctor = conn.execute("SELECT * FROM doctors WHERE user_id = ?", (current_user.id,)).fetchone()
    
    appointments = conn.execute("""
        SELECT a.*, p.name as patient_name, p.phone, p.age, p.gender, p.blood_group
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
        ORDER BY a.date DESC, a.time DESC
    """, (doctor['id'],)).fetchall()
    
    conn.close()
    
    return render_template('doctor_appointments.html', appointments=appointments)

@app.route('/doctor/complete/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@role_required(['doctor'])
def complete_appointment(appointment_id):
    conn = get_db()
    
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')
        
        conn.execute("UPDATE appointments SET status = 'Completed' WHERE id = ?", (appointment_id,))
        conn.execute("""INSERT INTO treatments (appointment_id, diagnosis, prescription, notes)
                       VALUES (?, ?, ?, ?)""",
                    (appointment_id, diagnosis, prescription, notes))
        conn.commit()
        conn.close()
        
        flash('Appointment completed successfully!', 'success')
        return redirect(url_for('doctor_appointments'))
    
    appointment = conn.execute("""
        SELECT a.*, p.name as patient_name, p.age, p.gender, p.blood_group, p.phone
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.id = ?
    """, (appointment_id,)).fetchone()
    
    patient_history = conn.execute("""
        SELECT a.date, a.time, t.diagnosis, t.prescription, t.notes
        FROM appointments a
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.patient_id = ? AND a.status = 'Completed'
        ORDER BY a.date DESC
    """, (appointment['patient_id'],)).fetchall()
    
    conn.close()
    
    return render_template('complete_appointment.html', appointment=appointment, patient_history=patient_history)

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
@role_required(['doctor'])
def doctor_availability():
    today = datetime.today().strftime('%Y-%m-%d')
    conn = get_db()
    doctor = conn.execute("SELECT * FROM doctors WHERE user_id = ?", (current_user.id,)).fetchone()
    
    if request.method == 'POST':
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        conn.execute("""INSERT INTO doctor_availability (doctor_id, date, start_time, end_time)
                       VALUES (?, ?, ?, ?)""",
                    (doctor['id'], date, start_time, end_time))
        conn.commit()
        flash('Availability added successfully!', 'success')
    
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    
    availabilities = conn.execute("""
        SELECT * FROM doctor_availability 
        WHERE doctor_id = ? AND date >= ? AND date <= ?
        ORDER BY date, start_time
    """, (doctor['id'], str(today), str(next_week))).fetchall()
    
    conn.close()
    
    return render_template('doctor_availability.html', availabilities=availabilities, today=today)

# Patient routes
@app.route('/patient/search-doctors')
@login_required
@role_required(['patient'])
def search_doctors():
    db = get_db()  # ← this is the connection with row_factory set

    specialization = request.args.get('specialization', '').strip()
    name = request.args.get('name', '').strip()

    sql = """
        SELECT d.*, dep.name AS department_name
        FROM doctors d
        LEFT JOIN departments dep ON d.department_id = dep.id
        WHERE d.is_active = 1
    """
    conditions = []
    params = []

    if specialization:
        conditions.append("dep.name LIKE ?")
        params.append(f"%{specialization}%")
    if name:
        conditions.append("d.name LIKE ?")
        params.append(f"%{name}%")

    if conditions:
        sql += " AND " + " AND ".join(conditions)

    sql += " ORDER BY d.name"

    # Critical: use db.execute(), not cursor.execute()
    doctors = db.execute(sql, params).fetchall()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()

    return render_template('search_doctors.html',
                           doctors=doctors,
                           departments=departments,
                           specialization=specialization,
                           name=name)

@app.route('/patient/book-appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@role_required(['patient'])
def book_appointment(doctor_id):
    conn = get_db()
    
    if request.method == 'POST':
        date = request.form.get('date')
        time = request.form.get('time')
        reason = request.form.get('reason')
        
        patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (current_user.id,)).fetchone()
        
        # Check if slot is available
        existing = conn.execute("""
            SELECT * FROM appointments 
            WHERE doctor_id = ? AND date = ? AND time = ? AND status != 'Cancelled'
        """, (doctor_id, date, time)).fetchone()
        
        if existing:
            flash('This time slot is already booked!', 'danger')
        else:
            conn.execute("""INSERT INTO appointments (patient_id, doctor_id, date, time, reason)
                           VALUES (?, ?, ?, ?, ?)""",
                        (patient['id'], doctor_id, date, time, reason))
            conn.commit()
            flash('Appointment booked successfully!', 'success')
            conn.close()
            return redirect(url_for('dashboard'))
    
    doctor = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    print(doctor['department_id'])
    dept=conn.execute('SELECT name FROM departments WHERE id=?',(doctor['department_id'],)).fetchone()
    d=dept[0]
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    
    availabilities = conn.execute("""
        SELECT * FROM doctor_availability 
        WHERE doctor_id = ? AND date >= ? AND date <= ? AND is_available = 1
        ORDER BY date, start_time
    """, (doctor_id, str(today), str(next_week))).fetchall()
    
    conn.close()
    
    return render_template('book_appointment.html', doctor=doctor, depart=d ,availabilities=availabilities)

@app.route('/patient/cancel-appointment/<int:appointment_id>')
@login_required
@role_required(['patient'])
def cancel_appointment(appointment_id):
    conn = get_db()
    
    conn.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    
    flash('Appointment cancelled successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/patient/profile', methods=['GET', 'POST'])
@login_required
@role_required(['patient'])
def patient_profile():
    conn = get_db()
    
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        blood_group = request.form.get('blood_group')
        
        conn.execute("""UPDATE patients 
                       SET name = ?, age = ?, gender = ?, phone = ?, email = ?, address = ?, blood_group = ?
                       WHERE user_id = ?""",
                    (name, age, gender, phone, email, address, blood_group, current_user.id))
        conn.commit()
        flash('Profile updated successfully!', 'success')
    
    patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (current_user.id,)).fetchone()
    conn.close()
    
    return render_template('patient_profile.html', patient=patient)

# API Routes (Optional)
@app.route('/api/doctors', methods=['GET'])
@login_required
def api_doctors():
    conn = get_db()
    doctors = conn.execute("SELECT * FROM doctors WHERE is_active = 1").fetchall()
    conn.close()
    
    return jsonify([dict(doctor) for doctor in doctors])

@app.route('/api/appointments/<int:doctor_id>', methods=['GET'])
@login_required
def api_doctor_appointments(doctor_id):
    conn = get_db()
    appointments = conn.execute("""
        SELECT a.*, p.name as patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
        ORDER BY a.date, a.time
    """, (doctor_id,)).fetchall()
    conn.close()
    
    return jsonify([dict(apt) for apt in appointments])

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        init_db()
        print("Database initialized successfully!")
    init_db()
    app.run(debug=True)