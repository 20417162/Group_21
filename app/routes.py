from flask import Blueprint, render_template, url_for, request, redirect, flash, Response, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import base64
from datetime import datetime, date
from collections import defaultdict
from functools import wraps
from sqlalchemy import func
from app import db
from app.models import User, AikidoInformation, Attachment, TrainingAttendance, ProofOfPayment

main = Blueprint('main', __name__)

# Admin decorator
def admin_required(f):
    """Decorator to require admin privileges for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'danger')
            return redirect(url_for('main.index', _anchor='login'))
        if not current_user.admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
def index():
    return render_template('index.html', title='Akido - Home')

@main.route('/register', methods=['POST'])
def register():
    first_name = request.form.get('first_name')
    surname = request.form.get('surname')
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Server-side validation
    if not all([first_name, surname, username, password, confirm_password]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('main.index', _anchor='login'))

    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('main.index', _anchor='login'))

    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'danger')
        return redirect(url_for('main.index', _anchor='login'))

    # Check if username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Username already exists. Please choose a different one.', 'danger')
        return redirect(url_for('main.index', _anchor='login'))

    # Create new user
    user = User(
        first_name=first_name,
        surname=surname,
        username=username
    )
    user.set_password(password)

    # Add to database
    db.session.add(user)
    db.session.commit()

    # Log the user in
    login_user(user)

    flash('Registration successful! You are now logged in.', 'success')
    return redirect(url_for('main.profile'))

@main.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Server-side validation
    if not all([username, password]):
        flash('Username and password are required.', 'danger')
        return redirect(url_for('main.index', _anchor='login'))

    # Find user by username
    user = User.query.filter_by(username=username).first()

    # Check if user exists and password is correct
    if user and user.check_password(password):
        login_user(user)
        flash('Login successful! Welcome back.', 'success')
        return redirect(url_for('main.profile'))
    else:
        flash('Invalid username or password.', 'danger')
        return redirect(url_for('main.index', _anchor='login'))

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@main.route('/profile')
@login_required
def profile():
    # Get the user's certificate if it exists
    certificate = Attachment.query.filter_by(
        user_id=current_user.id,
        type='aikido_certificate'
    ).first()
    
    # Get the user's profile picture if it exists
    profile_picture = Attachment.query.filter_by(
        user_id=current_user.id,
        type='profile_picture'
    ).first()
    
    # Get and organize training attendance data
    training_sessions = TrainingAttendance.query.filter_by(
        user_id=current_user.id
    ).order_by(TrainingAttendance.training_date.desc()).all()
    
    # Group training sessions by month/year
    training_by_month = defaultdict(list)
    monthly_totals = defaultdict(float)
    
    for session in training_sessions:
        month_key = session.training_date.strftime('%B %Y')
        training_by_month[month_key].append(session)
        monthly_totals[month_key] += session.hours
    
    # Sort months in descending order (most recent first)
    sorted_months = sorted(training_by_month.keys(), 
                          key=lambda x: datetime.strptime(x, '%B %Y'), 
                          reverse=True)
    
    # Get proof of payments (latest 6)
    proof_of_payments = ProofOfPayment.query.filter_by(
        user_id=current_user.id
    ).order_by(ProofOfPayment.created_at.desc()).limit(6).all()
    
    return render_template('profile.html', 
                         title='Profile — Aikido Pretoria',
                         certificate=certificate,
                         profile_picture=profile_picture,
                         training_by_month=training_by_month,
                         monthly_totals=monthly_totals,
                         sorted_months=sorted_months,
                         proof_of_payments=proof_of_payments)

@main.route('/profile/aikido', methods=['POST'])
@login_required
def save_aikido_info():
    import logging
    
    aikido_type = request.form.get('aikido_type', '').strip()
    aikido_rank = request.form.get('aikido_rank', '').strip()
    certificate_no = request.form.get('certificate_no', '').strip()
    afsa_no = request.form.get('afsa_no', '').strip()
    aif_no = request.form.get('aif_no', '').strip()
    honbu_no = request.form.get('honbu_no', '').strip()

    # Get or create AikidoInformation record for current user
    aikido_info = AikidoInformation.query.filter_by(user_id=current_user.id).first()
    
    if aikido_info:
        # Update existing record
        aikido_info.aikido_type = aikido_type if aikido_type else None
        aikido_info.aikido_rank = aikido_rank if aikido_rank else None
        aikido_info.certificate_no = certificate_no if certificate_no else None
        aikido_info.afsa_no = afsa_no if afsa_no else None
        aikido_info.aif_no = aif_no if aif_no else None
        aikido_info.honbu_no = honbu_no if honbu_no else None
        update_message = 'Aikido credentials updated successfully!'
    else:
        # Create new record
        aikido_info = AikidoInformation(
            user_id=current_user.id,
            aikido_type=aikido_type if aikido_type else None,
            aikido_rank=aikido_rank if aikido_rank else None,
            certificate_no=certificate_no if certificate_no else None,
            afsa_no=afsa_no if afsa_no else None,
            aif_no=aif_no if aif_no else None,
            honbu_no=honbu_no if honbu_no else None
        )
        db.session.add(aikido_info)
        update_message = 'Aikido credentials saved successfully!'

    # First, commit the aikido information (text fields)
    try:
        db.session.commit()
        flash(update_message, 'success')
        logging.info(f"Aikido info saved successfully for user {current_user.id}")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving aikido info for user {current_user.id}: {str(e)}")
        flash('Error saving Aikido credentials. Please try again.', 'danger')
        return redirect(url_for('main.profile'))

    # Handle certificate file upload separately
    certificate_file = request.files.get('certificate')
    if certificate_file and certificate_file.filename:
        try:
            # Validate file type
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
            filename = secure_filename(certificate_file.filename)
            if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
                flash('Invalid file type. Please upload a PDF, JPG, or PNG file.', 'danger')
                return redirect(url_for('main.profile'))
            
            # Validate file size (10MB limit)
            max_file_size = 10 * 1024 * 1024  # 10MB in bytes
            certificate_file.seek(0, 2)  # Move to end of file
            file_size = certificate_file.tell()
            certificate_file.seek(0)  # Reset to beginning
            
            if file_size > max_file_size:
                flash('File too large. Please upload a file smaller than 10MB.', 'danger')
                return redirect(url_for('main.profile'))
            
            # Remove any existing aikido certificate for this user
            existing_cert = Attachment.query.filter_by(
                user_id=current_user.id,
                type='aikido_certificate'
            ).first()
            if existing_cert:
                db.session.delete(existing_cert)
            
            # Read and encode file as base64
            file_data = certificate_file.read()
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            
            # Create new attachment
            new_attachment = Attachment(
                user_id=current_user.id,
                type='aikido_certificate',
                filename=filename,
                data=encoded_data
            )
            db.session.add(new_attachment)
            
            # Commit the certificate upload
            db.session.commit()
            flash('Certificate uploaded successfully!', 'success')
            logging.info(f"Certificate uploaded successfully for user {current_user.id}, filename: {filename}")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error uploading certificate for user {current_user.id}: {str(e)}")
            flash('Error uploading certificate. Your other information was saved successfully. Please try uploading the certificate again.', 'warning')
        
    return redirect(url_for('main.profile'))

@main.route('/profile/certificate/download')
@login_required
def download_certificate():
    # Find the user's aikido certificate
    certificate = Attachment.query.filter_by(
        user_id=current_user.id,
        type='aikido_certificate'
    ).first()
    
    if not certificate:
        flash('No certificate found.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Decode the base64 data
    try:
        file_data = base64.b64decode(certificate.data)
    except Exception as e:
        flash('Error retrieving certificate.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Determine content type based on file extension
    filename = certificate.filename.lower()
    if filename.endswith('.pdf'):
        mimetype = 'application/pdf'
    elif filename.endswith(('.jpg', '.jpeg')):
        mimetype = 'image/jpeg'
    elif filename.endswith('.png'):
        mimetype = 'image/png'
    else:
        mimetype = 'application/octet-stream'
    
    # Return the file as a download
    return Response(
        file_data,
        mimetype=mimetype,
        headers={
            'Content-Disposition': f'attachment; filename="{certificate.filename}"'
        }
    )
