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

# Profile Picture Routes
@main.route('/profile/picture/upload', methods=['POST'])
@login_required
def upload_profile_picture():
    import logging
    
    profile_picture_file = request.files.get('profile_picture')
    
    # Validate that a file was uploaded
    if not profile_picture_file or not profile_picture_file.filename:
        flash('Please select a profile picture to upload.', 'danger')
        return redirect(url_for('main.profile'))
    
    try:
        # Validate file type (only images)
        allowed_extensions = {'.jpg', '.jpeg', '.png'}
        filename = secure_filename(profile_picture_file.filename)
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            flash('Invalid file type. Please upload a JPG, JPEG, or PNG image.', 'danger')
            return redirect(url_for('main.profile'))
        
        # Validate file size (5MB limit for images)
        max_file_size = 5 * 1024 * 1024  # 5MB in bytes
        profile_picture_file.seek(0, 2)  # Move to end of file
        file_size = profile_picture_file.tell()
        profile_picture_file.seek(0)  # Reset to beginning
        
        if file_size > max_file_size:
            flash('File too large. Please upload an image smaller than 5MB.', 'danger')
            return redirect(url_for('main.profile'))
        
        # Remove any existing profile picture for this user
        existing_picture = Attachment.query.filter_by(
            user_id=current_user.id,
            type='profile_picture'
        ).first()
        if existing_picture:
            db.session.delete(existing_picture)
        
        # Read and encode file as base64
        file_data = profile_picture_file.read()
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        
        # Create new attachment
        new_attachment = Attachment(
            user_id=current_user.id,
            type='profile_picture',
            filename=filename,
            data=encoded_data
        )
        db.session.add(new_attachment)
        
        # Commit the profile picture upload
        db.session.commit()
        flash('Profile picture uploaded successfully!', 'success')
        logging.info(f"Profile picture uploaded successfully for user {current_user.id}, filename: {filename}")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error uploading profile picture for user {current_user.id}: {str(e)}")
        flash('Error uploading profile picture. Please try again.', 'danger')
    
    return redirect(url_for('main.profile'))

@main.route('/profile/picture/view')
@login_required
def view_profile_picture():
    # Find the user's profile picture
    profile_picture = Attachment.query.filter_by(
        user_id=current_user.id,
        type='profile_picture'
    ).first()
    
    if not profile_picture:
        # Return a 404 if no profile picture exists
        from flask import abort
        abort(404)
    
    # Decode the base64 data
    try:
        file_data = base64.b64decode(profile_picture.data)
    except Exception as e:
        from flask import abort
        abort(404)
    
    # Determine content type based on file extension
    filename = profile_picture.filename.lower()
    if filename.endswith(('.jpg', '.jpeg')):
        mimetype = 'image/jpeg'
    elif filename.endswith('.png'):
        mimetype = 'image/png'
    else:
        # Default to jpeg if extension is unclear
        mimetype = 'image/jpeg'
    
    # Return the image for display (not as download)
    return Response(
        file_data,
        mimetype=mimetype,
        headers={
            'Cache-Control': 'public, max-age=3600'  # Cache for 1 hour
        }
    )

# Training Attendance Routes
@main.route('/profile/training/add', methods=['POST'])
@login_required
def add_training():
    training_date_str = request.form.get('training_date')
    hours_str = request.form.get('hours')
    
    # Server-side validation
    if not all([training_date_str, hours_str]):
        flash('Training date and hours are required.', 'danger')
        return redirect(url_for('main.profile'))
    
    try:
        # Parse date
        training_date = datetime.strptime(training_date_str, '%Y-%m-%d').date()
        
        # Parse hours
        hours = float(hours_str)
        
        # Validate hours
        if hours <= 0:
            flash('Training hours must be greater than 0.', 'danger')
            return redirect(url_for('main.profile'))
        
        if hours > 24:
            flash('Training hours cannot exceed 24 hours per day.', 'danger')
            return redirect(url_for('main.profile'))
        
        # Check if entry already exists for this date
        existing_entry = TrainingAttendance.query.filter_by(
            user_id=current_user.id,
            training_date=training_date
        ).first()
        
        if existing_entry:
            flash('Training entry already exists for this date. Please use edit instead.', 'warning')
            return redirect(url_for('main.profile'))
        
        # Create new training entry
        new_training = TrainingAttendance(
            user_id=current_user.id,
            training_date=training_date,
            hours=hours
        )
        
        db.session.add(new_training)
        db.session.commit()
        
        flash(f'Training entry added successfully: {training_date.strftime("%B %d, %Y")} - {hours} hours', 'success')
        
    except ValueError:
        flash('Invalid date or hours format.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash('Error adding training entry. Please try again.', 'danger')
    
    return redirect(url_for('main.profile'))

@main.route('/profile/training/edit/<int:training_id>', methods=['POST'])
@login_required
def edit_training(training_id):
    # Get the training entry and verify ownership
    training_entry = TrainingAttendance.query.filter_by(
        id=training_id,
        user_id=current_user.id
    ).first()
    
    if not training_entry:
        flash('Training entry not found.', 'danger')
        return redirect(url_for('main.profile'))
    
    training_date_str = request.form.get('training_date')
    hours_str = request.form.get('hours')
    
    # Server-side validation
    if not all([training_date_str, hours_str]):
        flash('Training date and hours are required.', 'danger')
        return redirect(url_for('main.profile'))
    
    try:
        # Parse date
        training_date = datetime.strptime(training_date_str, '%Y-%m-%d').date()
        
        # Parse hours
        hours = float(hours_str)
        
        # Validate hours
        if hours <= 0:
            flash('Training hours must be greater than 0.', 'danger')
            return redirect(url_for('main.profile'))
        
        if hours > 24:
            flash('Training hours cannot exceed 24 hours per day.', 'danger')
            return redirect(url_for('main.profile'))
        
        # Check if another entry exists for the new date (if date changed)
        if training_date != training_entry.training_date:
            existing_entry = TrainingAttendance.query.filter_by(
                user_id=current_user.id,
                training_date=training_date
            ).first()
            
            if existing_entry:
                flash('Training entry already exists for this date.', 'warning')
                return redirect(url_for('main.profile'))
        
        # Update the entry
        old_date = training_entry.training_date.strftime("%B %d, %Y")
        training_entry.training_date = training_date
        training_entry.hours = hours
        
        db.session.commit()
        
        flash(f'Training entry updated successfully: {training_date.strftime("%B %d, %Y")} - {hours} hours', 'success')
        
    except ValueError:
        flash('Invalid date or hours format.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash('Error updating training entry. Please try again.', 'danger')
    
    return redirect(url_for('main.profile'))

@main.route('/profile/training/delete/<int:training_id>', methods=['POST'])
@login_required
def delete_training(training_id):
    # Get the training entry and verify ownership
    training_entry = TrainingAttendance.query.filter_by(
        id=training_id,
        user_id=current_user.id
    ).first()
    
    if not training_entry:
        flash('Training entry not found.', 'danger')
        return redirect(url_for('main.profile'))
    
    try:
        training_date = training_entry.training_date.strftime("%B %d, %Y")
        hours = training_entry.hours
        
        db.session.delete(training_entry)
        db.session.commit()
        
        flash(f'Training entry deleted successfully: {training_date} - {hours} hours', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting training entry. Please try again.', 'danger')
    
    return redirect(url_for('main.profile'))

# Proof of Payment Routes
@main.route('/profile/pop/upload', methods=['POST'])
@login_required
def upload_proof_of_payment():
    import logging
    
    pop_file = request.files.get('proof_of_payment')
    month_year = request.form.get('month_year', '').strip()
    
    # Server-side validation
    if not pop_file or not pop_file.filename:
        flash('Please select a proof of payment file to upload.', 'danger')
        return redirect(url_for('main.profile'))
    
    if not month_year:
        flash('Please specify the month and year for this payment.', 'danger')
        return redirect(url_for('main.profile'))
    
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
        filename = secure_filename(pop_file.filename)
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            flash('Invalid file type. Please upload a PDF, JPG, JPEG, or PNG file.', 'danger')
            return redirect(url_for('main.profile'))
        
        # Validate file size (5MB limit)
        max_file_size = 5 * 1024 * 1024  # 5MB in bytes
        pop_file.seek(0, 2)  # Move to end of file
        file_size = pop_file.tell()
        pop_file.seek(0)  # Reset to beginning
        
        if file_size > max_file_size:
            flash('File too large. Please upload a file smaller than 5MB.', 'danger')
            return redirect(url_for('main.profile'))
        
        # Check if proof of payment for this month already exists
        existing_pop = ProofOfPayment.query.filter_by(
            user_id=current_user.id,
            month_year=month_year
        ).first()
        
        if existing_pop:
            flash(f'Proof of payment for {month_year} already exists. Please delete it first if you want to replace it.', 'warning')
            return redirect(url_for('main.profile'))
        
        # Read and encode file as base64
        file_data = pop_file.read()
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        
        # Create new attachment
        new_attachment = Attachment(
            user_id=current_user.id,
            type='pop',
            filename=filename,
            data=encoded_data
        )
        db.session.add(new_attachment)
        db.session.flush()  # To get the attachment ID
        
        # Create new proof of payment
        new_pop = ProofOfPayment(
            user_id=current_user.id,
            attachment_id=new_attachment.id,
            month_year=month_year,
            admin_verified=False
        )
        db.session.add(new_pop)
        
        # Commit both records
        db.session.commit()
        flash(f'Proof of payment for {month_year} uploaded successfully!', 'success')
        logging.info(f"Proof of payment uploaded successfully for user {current_user.id}, month: {month_year}, filename: {filename}")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error uploading proof of payment for user {current_user.id}: {str(e)}")
        flash('Error uploading proof of payment. Please try again.', 'danger')
    
    return redirect(url_for('main.profile'))
