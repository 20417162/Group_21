# Akido - Flask Application
## Important
Please use the `seed.py` script to create an admin user and log in as them in order to make use of the admin dashboard.

Use the `seed_random_user.py` script to create dummy users in the database for admin dashboard purposes.

## Project Structure

```
akido/
├── app/                    # Application package
│   ├── __init__.py         # Flask app factory
│   ├── models.py           # SQLAlchemy models
│   ├── routes.py           # Application routes
│   ├── templates/          # Jinja2 templates
│   │   ├── base.html       # Base template with Bootstrap
│   │   ├── index.html      # Homepage
│   └── static/             # Static files (CSS, JS, assets)
│       ├── css/
│       ├── js/
        └── assets/
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Test configuration
│   └── test_app.py         # Application tests
├── migrations/             # Database migrations
├── venv/                   # Virtual environment
├── config.py               # Application configuration
├── requirements.txt        # Python dependencies
├── run.py                  # Application entry point
├── pytest.ini              # Test configuration
└── README.md              # This file
```

## Installation

1. **Clone the repository** (if applicable):
```bash
git clone https://github.com/20417162/Group_21.git
```

2. **Create and activate virtual environment**:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Unix/MacOS
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up MySQL database**:

   **Option A: Using Docker (Recommended)**
   
   Run a MySQL container:
   ```bash
   docker run --name mysql -e MYSQL_ROOT_PASSWORD=my-secret-pw -p 3306:3306 -d mysql:9.5
   ```
   
   Create the `akido` database:
   ```bash
   # Access the MySQL container
   docker exec -it mysql mysql -u root -p
   # Enter password: my-secret-pw
   
   # Create the database
   CREATE DATABASE akido;
   EXIT;
   ```
   
   **Docker Management Commands:**
   ```bash
   # Stop the container
   docker stop mysql
   
   # Start existing container
   docker start mysql
   
   # Remove the container (will delete all data)
   docker rm mysql
   
   # View container logs
   docker logs mysql
   ```

   **Option B: Manual Setup**
   - Install MySQL server locally
   - Create a MySQL database named `akido`
   - Update database credentials in `config.py` or set environment variables:

5. **Initialize database migrations**:
```bash
flask db upgrade
```

6. **Create an admin user** (optional):
```bash
python seed.py
```

## Admin User Setup

The application includes a seed script to create admin users. This is useful for initial setup or creating administrative accounts.

### Usage

```bash
python seed.py
```

### Command Line Options

The seed script supports the following arguments:

- `--username`: Username for the admin user
- `--password`: Password for the admin user (not recommended for production)
- `--first-name`: First name of the admin user
- `--surname`: Surname of the admin user

### Examples

**Interactive mode** (recommended for production):
```bash
python seed.py
```
The script will prompt for username, first name, surname, and password.

**Command line mode** (useful for development/testing):
```bash
python seed.py --username admin --first-name Admin --surname User --password mypassword
```

**Partial command line mode**:
```bash
python seed.py --username admin
```
The script will prompt for the missing fields.

### Help

For help and available options:
```bash
python seed.py --help
```

## Running the Application

### Development Mode

```bash
python run.py
```

Or using Flask CLI:

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
flask run
```

The application will be available at `http://localhost:3000`

### Production Mode

```bash
export FLASK_ENV=production
python run.py
```

## Running Tests

Run the complete test suite:

```bash
pytest
```

Run specific tests:

```bash
pytest tests/test_app.py -v
```

Run with coverage:

```bash
pytest --cov=app --cov-report=html
```

## Configuration

The application supports multiple configuration environments:

- **development**: Debug mode enabled, local database
- **production**: Optimized for production deployment

Set the environment using:

```bash
export FLASK_ENV=development  # or production
```

### Database Configuration

Update `config.py` or set environment variables:

```bash
export DATABASE_URL="mysql+pymysql://username:password@host:port/database"
```

## Technologies Used

- **Backend**: Flask, Flask-SQLAlchemy, Flask-Migrate
- **Database**: MySQL with PyMySQL connector
- **Testing**: pytest, pytest-flask
- **Frontend**: HTML, CSS, Bootstrap 5

