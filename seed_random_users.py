#!/usr/bin/env python3
"""
Random User Seed Script

This script creates random users in the database with optional unapproved proof of payments.
Usage: python seed_random_users.py --count <number_of_users>

Each user has a 10% chance of getting an unapproved proof of payment created.
"""

import os
import sys
import argparse
import random
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables BEFORE importing app modules
load_dotenv()

from app import create_app, db
from app.models import User, ProofOfPayment, Attachment


def get_random_first_name():
    """Get a random first name from a predefined list."""
    first_names = [
        'Alex', 'Blake', 'Cameron', 'Dakota', 'Ellis', 'Finley', 'Gray', 'Harper',
        'Jordan', 'Kendall', 'Logan', 'Morgan', 'Parker', 'Quinn', 'River', 'Sage',
        'Taylor', 'Avery', 'Casey', 'Drew', 'Emery', 'Frankie', 'Hayden', 'Jesse',
        'Kelly', 'Lane', 'Max', 'Noah', 'Oakley', 'Peyton', 'Reese', 'Sam', 'Tanner',
        'Blake', 'Chris', 'Dana', 'Eden', 'Flynn', 'Gale', 'Halo', 'Indigo', 'Jamie',
        'Kai', 'Lee', 'Merit', 'Nova', 'Ocean', 'Phoenix', 'Quincy', 'Rain', 'Sky'
    ]
    return random.choice(first_names)


def get_random_surname():
    """Get a random surname from a predefined list."""
    surnames = [
        'Anderson', 'Brown', 'Clark', 'Davis', 'Evans', 'Foster', 'Garcia', 'Harris',
        'Jackson', 'Johnson', 'Jones', 'King', 'Lewis', 'Miller', 'Moore', 'Nelson',
        'Parker', 'Roberts', 'Smith', 'Taylor', 'Thomas', 'Walker', 'White', 'Wilson',
        'Adams', 'Baker', 'Carter', 'Cooper', 'Edwards', 'Fisher', 'Green', 'Hall',
        'Hill', 'Hughes', 'Kelly', 'Lee', 'Martin', 'Murphy', 'Phillips', 'Rogers',
        'Scott', 'Stewart', 'Turner', 'Ward', 'Wood', 'Young', 'Allen', 'Bell'
    ]
    return random.choice(surnames)


def generate_username(first_name, surname, user_number):
    """Generate a unique username."""
    # Create username from first letter of first name + surname + number
    base_username = f"{first_name[0].lower()}{surname.lower()}{user_number:03d}"
    return base_username


def create_blank_attachment(user_id, attachment_type='proof_of_payment'):
    """Create a blank attachment for proof of payment."""
    try:
        attachment = Attachment(
            user_id=user_id,
            type=attachment_type,
            filename='placeholder_payment.pdf',
            data=''  # Blank as requested
        )
        db.session.add(attachment)
        db.session.flush()  # Get the ID without committing
        return attachment.id
    except Exception as e:
        print(f"Error creating attachment for user {user_id}: {str(e)}")
        return None


def create_proof_of_payment(user_id, attachment_id):
    """Create an unapproved proof of payment."""
    try:
        # Get current month and year
        current_date = datetime.now()
        month_year = current_date.strftime("%B %Y")
        
        proof_of_payment = ProofOfPayment(
            user_id=user_id,
            attachment_id=attachment_id,
            month_year=month_year,
            admin_verified=False  # Unapproved as requested
        )
        db.session.add(proof_of_payment)
        return True
    except Exception as e:
        print(f"Error creating proof of payment for user {user_id}: {str(e)}")
        return False


def create_random_users(count):
    """
    Create random users with optional proof of payments.
    
    Args:
        count (int): Number of users to create
    
    Returns:
        dict: Statistics about created users and proof of payments
    """
    stats = {
        'users_created': 0,
        'proof_of_payments_created': 0,
        'errors': 0
    }
    
    print(f"Creating {count} random users...")
    
    for i in range(1, count + 1):
        try:
            # Generate random user data
            first_name = get_random_first_name()
            surname = get_random_surname()
            username = generate_username(first_name, surname, i)
            
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                # Try with a different number
                username = f"{username}_alt"
            
            # Create user
            user = User(
                username=username,
                first_name=first_name,
                surname=surname,
                admin=False
            )
            user.set_password('password123')  # Default password for test users
            
            db.session.add(user)
            db.session.flush()  # Get the user ID without committing
            
            print(f"Created user {i}/{count}: {username} ({first_name} {surname})")
            stats['users_created'] += 1
            
            # 10% chance of creating proof of payment
            if random.random() < 0.1:  # 10% chance
                attachment_id = create_blank_attachment(user.id)
                if attachment_id:
                    if create_proof_of_payment(user.id, attachment_id):
                        print(f"  -> Added unapproved proof of payment for {username}")
                        stats['proof_of_payments_created'] += 1
                    else:
                        stats['errors'] += 1
                else:
                    stats['errors'] += 1
            
        except Exception as e:
            stats['errors'] += 1
            print(f"Error creating user {i}: {str(e)}")
            db.session.rollback()
            continue
    
    try:
        db.session.commit()
        print(f"\nSUCCESS: Batch commit completed!")
    except Exception as e:
        db.session.rollback()
        print(f"Error during batch commit: {str(e)}")
        stats['errors'] += 1
    
    return stats


def main():
    """Main function to handle command line arguments and create random users."""
    parser = argparse.ArgumentParser(description='Create random users for the Aikido application')
    parser.add_argument('--count', type=int, required=True, help='Number of users to create')
    
    args = parser.parse_args()
    
    # Validate count
    if args.count <= 0:
        print("Error: Count must be a positive integer")
        sys.exit(1)
    
    if args.count > 1000:
        print("Warning: Creating more than 1000 users. This may take a while.")
        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    # Debug: Check if .env file exists and DATABASE_URL is loaded
    print("=== DEBUG: Environment Variables ===")
    env_file_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f".env file exists: {os.path.exists(env_file_path)}")
    print(f".env file path: {env_file_path}")
    database_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL from environment: {database_url}")
    
    # Create Flask app and initialize database
    print("Initializing application...")
    app = create_app()
    
    # Debug: Check what database URI Flask is actually using
    print("=== DEBUG: Flask Configuration ===")
    print(f"Database URI being used: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("===================================")
    
    with app.app_context():
        try:
            # Create database tables if they don't exist
            db.create_all()
            
            # Create random users
            stats = create_random_users(args.count)
            
            # Print final statistics
            print("\n=== FINAL STATISTICS ===")
            print(f"Users created: {stats['users_created']}")
            print(f"Proof of payments created: {stats['proof_of_payments_created']}")
            print(f"Errors encountered: {stats['errors']}")
            print(f"Success rate: {((stats['users_created'] - stats['errors']) / args.count * 100):.1f}%")
            
            if stats['proof_of_payments_created'] > 0:
                print(f"Proof of payment rate: {(stats['proof_of_payments_created'] / stats['users_created'] * 100):.1f}%")
            
            print("Seed script completed!")
            
        except Exception as e:
            print(f"Failed to initialize database or create users: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()
