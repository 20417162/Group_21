import pytest
from app import create_app
from app.models import db

@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app('development')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

def test_index_page(client):
    """Test the index page loads successfully."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Aikido Pretoria' in response.data
    assert b'Welcome to Aikido Pretoria' in response.data

def test_404_error(client):
    """Test 404 error handling."""
    response = client.get('/nonexistent')
    assert response.status_code == 404

def test_index_template_rendering(client):
    """Test that templates are rendered correctly."""
    response = client.get('/')
    assert b'Akido - Home' in response.data
    assert b'Bootstrap' in response.data

def test_navigation_links(client):
    """Test that navigation links work."""
    response = client.get('/')
    assert b'data-page="login"' in response.data
    assert b'Home</a>' in response.data

def test_register_route_success(client):
    """Test successful user registration."""
    response = client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Check that the user was redirected to profile page
    assert b'Profile' in response.data and b'Aikido Pretoria' in response.data

def test_register_password_mismatch(client):
    """Test registration with mismatched passwords."""
    response = client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password456'
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_register_password_too_short(client):
    """Test registration with password too short."""
    response = client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': '12345',
        'confirm_password': '12345'
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_register_username_exists(client):
    """Test registration with existing username."""
    # First, create a user
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Try to register again with same username
    response = client.post('/register', data={
        'first_name': 'Jane',
        'surname': 'Smith',
        'username': 'johndoe',
        'password': 'password456',
        'confirm_password': 'password456'
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_register_missing_fields(client):
    """Test registration with missing required fields."""
    response = client.post('/register', data={
        'first_name': '',  # Empty field
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_login_form_validation(client):
    """Test that login form validation still works."""
    response = client.post('/', data={
        # Simulate form submission without required fields
    }, follow_redirects=False)

    # Should still load the page normally (no redirect if not POST to register)
    response = client.get('/')
    assert b'Log in' in response.data

def test_login_successful(client):
    """Test successful login with valid credentials."""
    # First register a user
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Now logout to test login
    client.get('/logout')

    # Test successful login
    response = client.post('/login', data={
        'username': 'johndoe',
        'password': 'password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Check that the user was redirected to profile page
    assert b'Profile' in response.data and b'Aikido Pretoria' in response.data

def test_login_invalid_username(client):
    """Test login with non-existent username."""
    response = client.post('/login', data={
        'username': 'nonexistent',
        'password': 'password123'
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_login_wrong_password(client):
    """Test login with correct username but wrong password."""
    # First register a user
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Test with wrong password
    response = client.post('/login', data={
        'username': 'johndoe',
        'password': 'wrongpassword'
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_login_missing_username(client):
    """Test login with missing username."""
    response = client.post('/login', data={
        'username': '',
        'password': 'password123'
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_login_missing_password(client):
    """Test login with missing password."""
    response = client.post('/login', data={
        'username': 'johndoe',
        'password': ''
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_login_missing_fields(client):
    """Test login with both username and password missing."""
    response = client.post('/login', data={
        'username': '',
        'password': ''
    })

    assert response.status_code == 302  # Redirect back to login section
    assert '/#login' in response.headers.get('Location', '')

def test_logout_functionality(client):
    """Test logout functionality."""
    # First register and login a user
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Test logout
    response = client.get('/logout', follow_redirects=True)

    assert response.status_code == 200
    # Check that the user was redirected to home
    assert b'Akido - Home' in response.data


def test_authenticated_navigation_desktop(client):
    """Test that navigation shows Profile and Logout when logged in (desktop)."""
    # First register and login a user
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Check the home page navigation
    response = client.get('/')
    assert response.status_code == 200
    # Should have Profile link
    assert b'href="/profile"' in response.data
    # Should have Logout link
    assert b'href="/logout"' in response.data
    # Should NOT have Log in link
    assert b'data-page="login"' not in response.data


def test_authenticated_navigation_mobile(client):
    """Test that mobile navigation shows Profile and Logout when logged in."""
    # First register and login a user
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Check the home page navigation
    response = client.get('/')
    assert response.status_code == 200
    # Should have Profile link in mobile nav
    assert b'href="/profile"' in response.data
    # Should have Logout link in mobile nav
    assert b'href="/logout"' in response.data


def test_unauthenticated_navigation_desktop(client):
    """Test that navigation shows Log in when not logged in (desktop)."""
    # Ensure not logged in
    client.get('/logout')

    response = client.get('/')
    assert response.status_code == 200
    # Should have Log in link
    assert b'data-page="login"' in response.data
    # Should NOT have Profile or Logout links
    assert b'href="/profile"' not in response.data
    assert b'href="/logout"' not in response.data


def test_unauthenticated_navigation_mobile(client):
    """Test that mobile navigation shows Log in when not logged in."""
    # Ensure not logged in
    client.get('/logout')

    response = client.get('/')
    assert response.status_code == 200
    # Should have Log in link in mobile nav
    assert b'data-page="login"' in response.data
    # Should NOT have Profile or Logout links
    assert b'href="/profile"' not in response.data
    assert b'href="/logout"' not in response.data


def test_profile_page_requires_login(client):
    """Test that profile page redirects to login if not authenticated."""
    response = client.get('/profile')
    # Should redirect to login page
    assert response.status_code == 302
    assert '/?next=%2Fprofile' in response.headers.get('Location', '')  # Flask-Login redirects with next parameter


def test_profile_page_access_authenticated(client):
    """Test that profile page is accessible when authenticated."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Profile' in response.data
    assert b'Aikido Pretoria' in response.data
    assert b'John' in response.data  # First name
    assert b'Doe' in response.data   # Surname
    assert b'johndoe' in response.data  # Username


def test_profile_aikido_section_no_data(client):
    """Test that Aikido section shows empty form when no data exists."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    response = client.get('/profile')
    assert response.status_code == 200
    # Should show Aikido Credentials section
    assert b'Aikido Credentials' in response.data
    # Should show info message for first-time users
    assert b'Enter your Aikido credentials to complete your profile' in response.data
    # Should show form fields
    assert b'name="aikido_type"' in response.data
    assert b'name="aikido_rank"' in response.data
    assert b'name="afsa_no"' in response.data
    assert b'name="aif_no"' in response.data
    assert b'name="honbu_no"' in response.data
    # Should have Save button
    assert b'Save</button>' in response.data
    # Should NOT have Edit button (no data yet)
    assert b'id="editAikidoBtn"' not in response.data


def test_save_aikido_info_new(client):
    """Test saving Aikido information for the first time."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save Aikido information
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Should redirect back to profile page
    assert b'Profile' in response.data
    # Should show success message
    assert b'Aikido credentials saved successfully!' in response.data


def test_save_aikido_info_partial_data(client):
    """Test saving Aikido information with only some fields filled."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save partial Aikido information
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '',  # Empty
        'afsa_no': 'AFSA001',
        'aif_no': '',  # Empty
        'honbu_no': 'HONBU001'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Aikido credentials saved successfully!' in response.data


def test_profile_aikido_section_with_data(client):
    """Test that Aikido section shows saved data correctly."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save Aikido information
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    })

    # Check profile page shows the data
    response = client.get('/profile')
    assert response.status_code == 200
    # Should show saved data
    assert b'Aikikai' in response.data
    assert b'1st Dan' in response.data
    assert b'AFSA001' in response.data
    assert b'AIF001' in response.data
    assert b'HONBU001' in response.data
    # Should have Edit button
    assert b'id="editAikidoBtn"' in response.data
    # Should show last updated date
    assert b'Last updated:' in response.data


def test_profile_aikido_section_with_partial_data(client):
    """Test that Aikido section shows 'Not specified' for empty fields."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save partial Aikido information
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '',  # Empty
        'afsa_no': 'AFSA001',
        'aif_no': '',  # Empty
        'honbu_no': ''  # Empty
    })

    # Check profile page shows the data
    response = client.get('/profile')
    assert response.status_code == 200
    # Should show saved data
    assert b'Aikikai' in response.data
    assert b'AFSA001' in response.data
    # Should show "Not specified" for empty fields
    assert response.data.count(b'Not specified') >= 3  # For empty fields


def test_update_aikido_info(client):
    """Test updating existing Aikido information."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save initial Aikido information
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    })

    # Update Aikido information
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Ki Society',
        'aikido_rank': '2nd Dan',
        'afsa_no': 'AFSA002',
        'aif_no': 'AIF002',
        'honbu_no': 'HONBU002'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Should show updated message
    assert b'Aikido credentials updated successfully!' in response.data
    # Should show updated data
    assert b'Ki Society' in response.data
    assert b'2nd Dan' in response.data
    assert b'AFSA002' in response.data
    assert b'AIF002' in response.data
    assert b'HONBU002' in response.data


def test_save_aikido_info_empty_form(client):
    """Test saving completely empty Aikido form."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save empty Aikido information
    response = client.post('/profile/aikido', data={
        'aikido_type': '',
        'aikido_rank': '',
        'afsa_no': '',
        'aif_no': '',
        'honbu_no': ''
    }, follow_redirects=True)

    assert response.status_code == 200
    # Should still save successfully (all fields are optional)
    assert b'Aikido credentials saved successfully!' in response.data


def test_save_aikido_info_requires_login(client):
    """Test that saving Aikido info requires authentication."""
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    })
    # Should redirect to login page
    assert response.status_code == 302
    assert '/?next=%2Fprofile%2Faikido' in response.headers.get('Location', '')  # Flask-Login redirects with next parameter


def test_aikido_form_preserves_data_on_edit(client):
    """Test that edit form is pre-filled with existing data."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save Aikido information
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    })

    # Check that form values are preserved
    response = client.get('/profile')
    assert response.status_code == 200
    # Check that form inputs have the correct values
    assert b'value="Aikikai"' in response.data
    assert b'value="1st Dan"' in response.data
    assert b'value="AFSA001"' in response.data
    assert b'value="AIF001"' in response.data
    assert b'value="HONBU001"' in response.data


def test_aikido_javascript_toggle_functionality(client):
    """Test that JavaScript toggle function exists in profile page."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save some aikido data first so Edit button appears
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    })

    response = client.get('/profile')
    assert response.status_code == 200
    # Should include the JavaScript function
    assert b'function toggleAikidoEdit()' in response.data
    # Should have Edit button with onclick when data exists
    assert b'onclick="toggleAikidoEdit()"' in response.data


def test_save_certificate_no_field(client):
    """Test saving the certificate_no field."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save Aikido information with certificate_no
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'certificate_no': 'CERT-12345',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Aikido credentials saved successfully!' in response.data
    assert b'CERT-12345' in response.data


def test_profile_shows_certificate_no(client):
    """Test that profile page shows certificate number."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save Aikido information with certificate_no
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'certificate_no': 'CERT-12345',
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    })

    # Check profile page shows the certificate number
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Certificate No:' in response.data
    assert b'CERT-12345' in response.data


def test_upload_certificate_first_time(client):
    """Test uploading a certificate for the first time."""
    import io
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Create a fake PDF file
    fake_pdf = io.BytesIO(b'%PDF-1.4 fake pdf content')
    
    # Save Aikido information with certificate upload
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'certificate_no': 'CERT-12345',
        'certificate': (fake_pdf, 'test_certificate.pdf'),
        'afsa_no': 'AFSA001',
        'aif_no': 'AIF001',
        'honbu_no': 'HONBU001'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Certificate uploaded successfully!' in response.data


def test_replace_existing_certificate(client):
    """Test replacing an existing certificate ensures only one exists."""
    import io
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Upload first certificate
    fake_pdf1 = io.BytesIO(b'%PDF-1.4 fake pdf content 1')
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
        'certificate_no': 'CERT-12345',
        'certificate': (fake_pdf1, 'first_certificate.pdf'),
        'afsa_no': 'AFSA001'
    })

    # Upload second certificate (should replace first)
    fake_pdf2 = io.BytesIO(b'%PDF-1.4 fake pdf content 2')
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '2nd Dan',
        'certificate_no': 'CERT-67890',
        'certificate': (fake_pdf2, 'second_certificate.pdf'),
        'afsa_no': 'AFSA002'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Certificate uploaded successfully!' in response.data
    
    # Check that profile shows the new certificate
    response = client.get('/profile')
    assert b'second_certificate.pdf' in response.data
    # Should not show old certificate
    assert b'first_certificate.pdf' not in response.data


def test_download_certificate(client):
    """Test downloading an uploaded certificate."""
    import io
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Upload certificate
    fake_pdf_content = b'%PDF-1.4 fake pdf content for download test'
    fake_pdf = io.BytesIO(fake_pdf_content)
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'certificate': (fake_pdf, 'download_test.pdf'),
    })

    # Download the certificate
    response = client.get('/profile/certificate/download')
    assert response.status_code == 200
    assert response.data == fake_pdf_content
    assert 'application/pdf' in response.content_type
    assert 'attachment; filename="download_test.pdf"' in response.headers.get('Content-Disposition', '')


def test_download_certificate_not_found(client):
    """Test downloading certificate when none exists."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Try to download when no certificate exists
    response = client.get('/profile/certificate/download', follow_redirects=True)
    assert response.status_code == 200
    assert b'No certificate found.' in response.data


def test_download_certificate_requires_login(client):
    """Test that downloading certificate requires authentication."""
    response = client.get('/profile/certificate/download')
    assert response.status_code == 302
    assert '/?next=%2Fprofile%2Fcertificate%2Fdownload' in response.headers.get('Location', '')


def test_certificate_file_type_validation(client):
    """Test that only allowed file types can be uploaded."""
    import io
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Try to upload invalid file type
    fake_txt = io.BytesIO(b'This is a text file, not allowed')
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'certificate': (fake_txt, 'invalid.txt'),
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid file type. Please upload a PDF, JPG, or PNG file.' in response.data


def test_certificate_upload_various_formats(client):
    """Test uploading various allowed file formats."""
    import io
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Test PDF
    fake_pdf = io.BytesIO(b'%PDF-1.4 fake pdf')
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'certificate': (fake_pdf, 'test.pdf'),
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Certificate uploaded successfully!' in response.data

    # Test JPG
    fake_jpg = io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF fake jpg')
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'certificate': (fake_jpg, 'test.jpg'),
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Certificate uploaded successfully!' in response.data

    # Test PNG
    fake_png = io.BytesIO(b'\x89PNG\r\n\x1a\n fake png')
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'certificate': (fake_png, 'test.png'),
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Certificate uploaded successfully!' in response.data


def test_profile_shows_certificate_download_link(client):
    """Test that profile shows download link when certificate exists."""
    import io
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Upload certificate
    fake_pdf = io.BytesIO(b'%PDF-1.4 fake pdf')
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'certificate': (fake_pdf, 'mycert.pdf'),
    })

    # Check profile page shows download link
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'href="/profile/certificate/download"' in response.data
    assert b'mycert.pdf' in response.data
    assert b'fa-download' in response.data


def test_profile_shows_no_certificate_message(client):
    """Test that profile shows 'Not uploaded' when no certificate exists."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save aikido info without certificate
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '1st Dan',
    })

    # Check profile page shows "Not uploaded"
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Certificate:' in response.data
    assert b'Not uploaded' in response.data


def test_form_has_file_upload_attributes(client):
    """Test that the form has proper attributes for file upload."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    response = client.get('/profile')
    assert response.status_code == 200
    # Should have multipart form encoding
    assert b'enctype="multipart/form-data"' in response.data
    # Should have file input with correct accept attribute
    assert b'type="file"' in response.data
    assert b'accept=".pdf,.jpg,.jpeg,.png"' in response.data
    # Should have certificate_no input field
    assert b'name="certificate_no"' in response.data


def test_certificate_no_field_in_edit_form(client):
    """Test that certificate_no field appears in edit form."""
    # Register and login
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Save some data first
    client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'certificate_no': 'CERT-123',
    })

    response = client.get('/profile')
    assert response.status_code == 200
    # Should show certificate_no in view mode
    assert b'Certificate No:' in response.data
    assert b'CERT-123' in response.data
    # Should have certificate_no input field in edit form
    assert b'name="certificate_no"' in response.data
    assert b'value="CERT-123"' in response.data


def test_register_redirects_to_profile_without_following(client):
    """Test that register route redirects to profile page (without following redirects)."""
    response = client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=False)

    assert response.status_code == 302  # Redirect
    assert '/profile' in response.headers.get('Location', '')


def test_login_redirects_to_profile_without_following(client):
    """Test that login route redirects to profile page (without following redirects)."""
    # First register a user
    client.post('/register', data={
        'first_name': 'John',
        'surname': 'Doe',
        'username': 'johndoe',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Logout to test login
    client.get('/logout')

    # Test login redirect
    response = client.post('/login', data={
        'username': 'johndoe',
        'password': 'password123'
    }, follow_redirects=False)

    assert response.status_code == 302  # Redirect
    assert '/profile' in response.headers.get('Location', '')


def test_e2e_register_to_profile_flow(client):
    """Test end-to-end flow from registration to profile page access."""
    # Register a new user
    response = client.post('/register', data={
        'first_name': 'Jane',
        'surname': 'Smith',
        'username': 'janesmith',
        'password': 'securepass123',
        'confirm_password': 'securepass123'
    }, follow_redirects=True)

    # Should be on profile page
    assert response.status_code == 200
    assert b'Profile' in response.data and b'Aikido Pretoria' in response.data
    assert b'Jane' in response.data
    assert b'Smith' in response.data
    assert b'janesmith' in response.data
    
    # Should show empty aikido form for new user
    assert b'Enter your Aikido credentials to complete your profile' in response.data


def test_e2e_login_to_profile_flow(client):
    """Test end-to-end flow from login to profile page access."""
    # First register a user
    client.post('/register', data={
        'first_name': 'Mike',
        'surname': 'Johnson',
        'username': 'mikejohnson',
        'password': 'testpass456',
        'confirm_password': 'testpass456'
    })

    # Save some profile data
    client.post('/profile/aikido', data={
        'aikido_type': 'Yoshinkan',
        'aikido_rank': '3rd Kyu',
        'afsa_no': 'AFSA999',
    })

    # Logout
    client.get('/logout')

    # Login and verify redirect to profile
    response = client.post('/login', data={
        'username': 'mikejohnson',
        'password': 'testpass456'
    }, follow_redirects=True)

    # Should be on profile page with existing data
    assert response.status_code == 200
    assert b'Profile' in response.data and b'Aikido Pretoria' in response.data
    assert b'Mike' in response.data
    assert b'Johnson' in response.data
    assert b'mikejohnson' in response.data
    
    # Should show saved aikido data
    assert b'Yoshinkan' in response.data
    assert b'3rd Kyu' in response.data
    assert b'AFSA999' in response.data


def test_profile_redirect_preserves_user_session(client):
    """Test that profile redirect maintains user session correctly."""
    # Register user
    client.post('/register', data={
        'first_name': 'Test',
        'surname': 'User',
        'username': 'testuser',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Should be able to access profile directly after redirect
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Test' in response.data
    assert b'User' in response.data

    # Should be able to save data without re-authentication
    response = client.post('/profile/aikido', data={
        'aikido_type': 'Aikikai',
        'aikido_rank': '5th Kyu',
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Aikido credentials saved successfully!' in response.data
