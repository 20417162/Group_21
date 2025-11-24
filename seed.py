#!/usr/bin/env python3
"""
Admin User Seed Script

This script creates an admin user in the database.
Usage: python seed.py [--username <username>] [--password <password>]

If username or password are not provided as arguments, the script will prompt for them.
"""

import os
import sys
import argparse
import getpass
from dotenv import load_dotenv

# Load environment variables BEFORE importing app modules
load_dotenv()

from app import create_app, db
from app.models import User


def create_admin_user(username, first_name, surname, password):
    """
    Create an admin user with the specified credentials.
    
    Args:
        username (str): The username for the admin user
        first_name (str): First name of the admin user
        surname (str): Surname of the admin user
        password (str): Plain text password (will be hashed)
    
    Returns:
        bool: True if user was created successfully, False otherwise
    """
    try:
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"Error: User with username '{username}' already exists.")
            return False
        
        # Create new admin user
        admin_user = User(
            username=username,
            first_name=first_name,
            surname=surname,
            admin=True
        )
        admin_user.set_password(password)
        
        # Add to database
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"SUCCESS: Admin user '{username}' created successfully!")
        print(f"Name: {first_name} {surname}")
        print(f"Admin: Yes")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {str(e)}")
        return False


def main():
    """Main function to handle command line arguments and create admin user."""
    parser = argparse.ArgumentParser(description='Create an admin user for the Aikido application')
    parser.add_argument('--username', type=str, help='Username for the admin user')
    parser.add_argument('--password', type=str, help='Password for the admin user')
    parser.add_argument('--first-name', type=str, help='First name of the admin user')
    parser.add_argument('--surname', type=str, help='Surname of the admin user')
    
    args = parser.parse_args()

    # Get username
    if args.username:
        username = args.username
    else:
        username = input("Enter admin username: ").strip()
        if not username:
            print("Error: Username cannot be empty")
            sys.exit(1)
    
    # Get first name
    if args.first_name:
        first_name = args.first_name
    else:
        first_name = input("Enter first name: ").strip()
        if not first_name:
            print("Error: First name cannot be empty")
            sys.exit(1)
    
    # Get surname
    if args.surname:
        surname = args.surname
    else:
        surname = input("Enter surname: ").strip()
        if not surname:
            print("Error: Surname cannot be empty")
            sys.exit(1)
    
    # Get password
    if args.password:
        password = args.password
        print("Warning: Password provided via command line argument. This is not secure for production use.")
    else:
        password = getpass.getpass("Enter admin password: ")
        if not password:
            print("Error: Password cannot be empty")
            sys.exit(1)
        
        # Confirm password
        password_confirm = getpass.getpass("Confirm admin password: ")
        if password != password_confirm:
            print("Error: Passwords do not match")
            sys.exit(1)
    
    # Validate password strength
    if len(password) < 6:
        print("Error: Password must be at least 6 characters long")
        sys.exit(1)
    
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
            
            # Create admin user
            print(f"Creating admin user '{username}'...")
            success = create_admin_user(username, first_name, surname, password)
            
            if success:
                print("Seed script completed successfully!")
                sys.exit(0)
            else:
                sys.exit(1)
                
        except Exception as e:
            print(f"Failed to initialize database or create user: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()
