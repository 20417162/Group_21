import pytest
import io
import base64
from app import create_app, db
from app.models import User, AikidoInformation, Attachment


@pytest.fixture
def app():
    app = create_app()
    app.config.from_object('config.TestingConfig')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_user(client):
    """Create and login a test user"""
    # Register a user
    client.post('/register', data={
        'first_name': 'Test',
        'surname': 'User',
        'username': 'testuser',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    
    # Login the user
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    return User.query.filter_by(username='testuser').first()


class TestAikidoProfile:
    
    def test_save_aikido_info_without_certificate(self, client, auth_user):
        """Test saving aikido information without certificate upload"""
        response = client.post('/profile/aikido', data={
            'aikido_type': 'Aikikai',
            'aikido_rank': '1st Dan',
            'certificate_no': 'CERT-12345',
            'afsa_no': 'AFSA-6789',
            'aif_no': 'AIF-1111',
            'honbu_no': 'HONBU-2222'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Aikido credentials saved successfully!' in response.data or b'Aikido credentials updated successfully!' in response.data
        
        # Verify data was saved to database
        aikido_info = AikidoInformation.query.filter_by(user_id=auth_user.id).first()
        assert aikido_info is not None
        assert aikido_info.aikido_type == 'Aikikai'
        assert aikido_info.aikido_rank == '1st Dan'
        assert aikido_info.certificate_no == 'CERT-12345'
        assert aikido_info.afsa_no == 'AFSA-6789'
        assert aikido_info.aif_no == 'AIF-1111'
        assert aikido_info.honbu_no == 'HONBU-2222'

    def test_save_aikido_info_with_valid_certificate(self, client, auth_user):
        """Test saving aikido information with valid certificate upload"""
        # Create a fake PDF file
        fake_pdf_content = b'%PDF-1.4 fake pdf content for testing'
        
        response = client.post('/profile/aikido', data={
            'aikido_type': 'Aikikai',
            'aikido_rank': '2nd Dan',
            'certificate_no': 'CERT-54321',
            'afsa_no': 'AFSA-9876',
            'certificate': (io.BytesIO(fake_pdf_content), 'test_certificate.pdf')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Aikido credentials saved successfully!' in response.data or b'Aikido credentials updated successfully!' in response.data
        assert b'Certificate uploaded successfully!' in response.data
        
        # Verify aikido info was saved
        aikido_info = AikidoInformation.query.filter_by(user_id=auth_user.id).first()
        assert aikido_info is not None
        assert aikido_info.aikido_type == 'Aikikai'
        assert aikido_info.aikido_rank == '2nd Dan'
        assert aikido_info.certificate_no == 'CERT-54321'
        assert aikido_info.afsa_no == 'AFSA-9876'
        
        # Verify certificate was uploaded
        certificate = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='aikido_certificate'
        ).first()
        assert certificate is not None
        assert certificate.filename == 'test_certificate.pdf'
        
        # Verify certificate content
        decoded_content = base64.b64decode(certificate.data)
        assert decoded_content == fake_pdf_content

    def test_save_aikido_info_with_invalid_file_type(self, client, auth_user):
        """Test that invalid file types are rejected but other data still saves"""
        fake_txt_content = b'This is a text file, not a certificate'
        
        response = client.post('/profile/aikido', data={
            'aikido_type': 'Yoshinkai',
            'aikido_rank': '3rd Kyu',
            'certificate_no': 'CERT-99999',
            'certificate': (io.BytesIO(fake_txt_content), 'invalid_file.txt')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid file type' in response.data
        
        # Even with invalid file, the text data should still be saved
        aikido_info = AikidoInformation.query.filter_by(user_id=auth_user.id).first()
        assert aikido_info is not None
        assert aikido_info.aikido_type == 'Yoshinkai'
        assert aikido_info.aikido_rank == '3rd Kyu'
        assert aikido_info.certificate_no == 'CERT-99999'
        
        # No certificate should be uploaded
        certificate = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='aikido_certificate'
        ).first()
        assert certificate is None

    def test_save_aikido_info_with_oversized_file(self, client, auth_user):
        """Test that oversized files are rejected but other data still saves"""
        # Create a file larger than 10MB (10 * 1024 * 1024 = 10485760)
        oversized_content = b'x' * (11 * 1024 * 1024)  # 11MB
        
        response = client.post('/profile/aikido', data={
            'aikido_type': 'Ki Society',
            'aikido_rank': '5th Kyu',
            'certificate_no': 'CERT-BIG',
            'certificate': (io.BytesIO(oversized_content), 'big_certificate.pdf')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'File too large' in response.data
        
        # Text data should still be saved
        aikido_info = AikidoInformation.query.filter_by(user_id=auth_user.id).first()
        assert aikido_info is not None
        assert aikido_info.aikido_type == 'Ki Society'
        assert aikido_info.aikido_rank == '5th Kyu'
        assert aikido_info.certificate_no == 'CERT-BIG'
        
        # No certificate should be uploaded
        certificate = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='aikido_certificate'
        ).first()
        assert certificate is None

    def test_update_existing_aikido_info(self, client, auth_user):
        """Test updating existing aikido information"""
        # First, create some initial data
        client.post('/profile/aikido', data={
            'aikido_type': 'Initial Type',
            'certificate_no': 'INITIAL-CERT'
        })
        
        # Now update it
        response = client.post('/profile/aikido', data={
            'aikido_type': 'Updated Type',
            'aikido_rank': 'Updated Rank',
            'certificate_no': 'UPDATED-CERT',
            'afsa_no': 'NEW-AFSA'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Aikido credentials updated successfully!' in response.data
        
        # Verify the update
        aikido_info = AikidoInformation.query.filter_by(user_id=auth_user.id).first()
        assert aikido_info.aikido_type == 'Updated Type'
        assert aikido_info.aikido_rank == 'Updated Rank'
        assert aikido_info.certificate_no == 'UPDATED-CERT'
        assert aikido_info.afsa_no == 'NEW-AFSA'

    def test_replace_existing_certificate(self, client, auth_user):
        """Test replacing an existing certificate with a new one"""
        # Upload first certificate
        old_pdf = b'%PDF-1.4 old certificate content'
        client.post('/profile/aikido', data={
            'aikido_type': 'Test Type',
            'certificate_no': 'OLD-CERT',
            'certificate': (io.BytesIO(old_pdf), 'old_cert.pdf')
        })
        
        # Upload new certificate
        new_pdf = b'%PDF-1.4 new certificate content'
        response = client.post('/profile/aikido', data={
            'aikido_type': 'Test Type',
            'certificate_no': 'NEW-CERT',
            'certificate': (io.BytesIO(new_pdf), 'new_cert.pdf')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Certificate uploaded successfully!' in response.data
        
        # Should only have one certificate (the new one)
        certificates = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='aikido_certificate'
        ).all()
        assert len(certificates) == 1
        assert certificates[0].filename == 'new_cert.pdf'
        
        # Verify certificate content is the new one
        decoded_content = base64.b64decode(certificates[0].data)
        assert decoded_content == new_pdf

    def test_profile_page_shows_certificate_info(self, client, auth_user):
        """Test that the profile page correctly displays certificate information"""
        # Upload some data with certificate
        fake_pdf = b'%PDF-1.4 test certificate'
        client.post('/profile/aikido', data={
            'aikido_type': 'Display Test',
            'certificate_no': 'DISPLAY-CERT',
            'certificate': (io.BytesIO(fake_pdf), 'display_cert.pdf')
        })
        
        # Check the profile page displays the info
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'Display Test' in response.data
        assert b'DISPLAY-CERT' in response.data
        assert b'display_cert.pdf' in response.data

    def test_certificate_download(self, client, auth_user):
        """Test downloading a certificate"""
        # Upload a certificate first
        fake_pdf = b'%PDF-1.4 downloadable certificate'
        client.post('/profile/aikido', data={
            'certificate': (io.BytesIO(fake_pdf), 'download_test.pdf')
        })
        
        # Download the certificate
        response = client.get('/profile/certificate/download')
        assert response.status_code == 200
        assert response.data == fake_pdf
        assert response.headers['Content-Disposition'] == 'attachment; filename="download_test.pdf"'
