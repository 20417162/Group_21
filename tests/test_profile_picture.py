import pytest
import io
import base64
from app import create_app, db
from app.models import User, Attachment


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


class TestProfilePicture:
    
    def test_upload_valid_jpg_profile_picture(self, client, auth_user):
        """Test uploading a valid JPG profile picture"""
        # Create a fake JPG file
        fake_jpg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'  # JPG header
        
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_jpg_content), 'test_profile.jpg')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Profile picture uploaded successfully!' in response.data
        
        # Verify profile picture was saved to database
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is not None
        assert profile_picture.filename == 'test_profile.jpg'
        
        # Verify profile picture content
        decoded_content = base64.b64decode(profile_picture.data)
        assert decoded_content == fake_jpg_content

    def test_upload_valid_png_profile_picture(self, client, auth_user):
        """Test uploading a valid PNG profile picture"""
        # Create a fake PNG file
        fake_png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'  # PNG header
        
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_png_content), 'test_profile.png')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Profile picture uploaded successfully!' in response.data
        
        # Verify profile picture was saved to database
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is not None
        assert profile_picture.filename == 'test_profile.png'
        
        # Verify profile picture content
        decoded_content = base64.b64decode(profile_picture.data)
        assert decoded_content == fake_png_content

    def test_upload_valid_jpeg_profile_picture(self, client, auth_user):
        """Test uploading a valid JPEG profile picture"""
        # Create a fake JPEG file
        fake_jpeg_content = b'\xff\xd8\xff\xe1\x00\x10Exif\x00\x00'  # JPEG header with Exif
        
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_jpeg_content), 'test_profile.jpeg')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Profile picture uploaded successfully!' in response.data
        
        # Verify profile picture was saved to database
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is not None
        assert profile_picture.filename == 'test_profile.jpeg'

    def test_upload_invalid_file_type(self, client, auth_user):
        """Test that invalid file types are rejected"""
        fake_txt_content = b'This is a text file, not an image'
        
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_txt_content), 'invalid_file.txt')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid file type. Please upload a JPG, JPEG, or PNG image.' in response.data
        
        # No profile picture should be uploaded
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is None

    def test_upload_oversized_file(self, client, auth_user):
        """Test that oversized files are rejected"""
        # Create a file larger than 5MB (5 * 1024 * 1024 = 5242880)
        oversized_content = b'x' * (6 * 1024 * 1024)  # 6MB
        
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(oversized_content), 'big_image.jpg')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'File too large. Please upload an image smaller than 5MB.' in response.data
        
        # No profile picture should be uploaded
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is None

    def test_upload_no_file_selected(self, client, auth_user):
        """Test uploading without selecting a file"""
        response = client.post('/profile/picture/upload', data={}, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Please select a profile picture to upload.' in response.data
        
        # No profile picture should be uploaded
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is None

    def test_replace_existing_profile_picture(self, client, auth_user):
        """Test replacing an existing profile picture with a new one"""
        # Upload first profile picture
        old_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF old image'
        client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(old_jpg), 'old_profile.jpg')
        })
        
        # Upload new profile picture
        new_png = b'\x89PNG\r\n\x1a\n new image content'
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(new_png), 'new_profile.png')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Profile picture uploaded successfully!' in response.data
        
        # Should only have one profile picture (the new one)
        profile_pictures = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).all()
        assert len(profile_pictures) == 1
        assert profile_pictures[0].filename == 'new_profile.png'
        
        # Verify profile picture content is the new one
        decoded_content = base64.b64decode(profile_pictures[0].data)
        assert decoded_content == new_png

    def test_view_profile_picture(self, client, auth_user):
        """Test viewing an uploaded profile picture"""
        # Upload a profile picture first
        fake_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF test view image'
        client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_jpg), 'view_test.jpg')
        })
        
        # View the profile picture
        response = client.get('/profile/picture/view')
        assert response.status_code == 200
        assert response.data == fake_jpg
        assert response.headers['Content-Type'] == 'image/jpeg'
        assert 'max-age=3600' in response.headers['Cache-Control']

    def test_view_nonexistent_profile_picture(self, client, auth_user):
        """Test viewing profile picture when none exists"""
        response = client.get('/profile/picture/view')
        assert response.status_code == 404

    def test_profile_page_shows_profile_picture_info(self, client, auth_user):
        """Test that the profile page correctly displays profile picture information"""
        # Test profile page without profile picture
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'Upload Profile Picture' in response.data
        
        # Upload a profile picture
        fake_png = b'\x89PNG\r\n\x1a\n test display image'
        client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_png), 'display_test.png')
        })
        
        # Check the profile page displays the profile picture
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'/profile/picture/view' in response.data  # Profile picture URL
        assert b'Profile Picture' in response.data  # Text displayed when picture exists

    def test_profile_page_shows_default_when_no_picture(self, client, auth_user):
        """Test that the profile page shows default avatar when no picture uploaded"""
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'fa-user' in response.data  # Default user icon
        assert b'Upload Profile Picture' in response.data

    def test_view_png_profile_picture_content_type(self, client, auth_user):
        """Test that PNG files are served with correct content type"""
        fake_png = b'\x89PNG\r\n\x1a\n test png content type'
        client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_png), 'content_type_test.png')
        })
        
        response = client.get('/profile/picture/view')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'image/png'

    def test_view_jpeg_profile_picture_content_type(self, client, auth_user):
        """Test that JPEG files are served with correct content type"""
        fake_jpeg = b'\xff\xd8\xff\xe1\x00\x10Exif\x00\x00 test jpeg'
        client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_jpeg), 'content_type_test.jpeg')
        })
        
        response = client.get('/profile/picture/view')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'image/jpeg'

    def test_unauthorized_access_upload(self, client):
        """Test that unauthorized users cannot upload profile pictures"""
        # Don't login, try to upload
        fake_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF unauthorized test'
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_jpg), 'unauthorized.jpg')
        }, follow_redirects=True)
        
        # Should redirect to login page or show login form
        assert response.status_code == 200
        # Should not have uploaded the image
        assert Attachment.query.filter_by(type='profile_picture').first() is None

    def test_unauthorized_access_view(self, client):
        """Test that unauthorized users cannot view profile pictures"""
        response = client.get('/profile/picture/view')
        assert response.status_code in [401, 302]  # Unauthorized or redirect to login

    def test_profile_picture_modal_functionality(self, client, auth_user):
        """Test that profile picture upload modal is present and functional"""
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'profilePictureModal' in response.data
        assert b'Upload Profile Picture' in response.data
        assert b'/profile/picture/upload' in response.data
        assert b'enctype="multipart/form-data"' in response.data

    def test_security_filename_sanitization(self, client, auth_user):
        """Test that filenames are properly sanitized"""
        fake_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF security test'
        
        # Try uploading with a potentially dangerous filename
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(fake_jpg), '../../../malicious.jpg')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Profile picture uploaded successfully!' in response.data
        
        # Check that the filename was sanitized
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is not None
        # werkzeug.secure_filename should have sanitized this
        assert not profile_picture.filename.startswith('../')
        assert 'malicious.jpg' in profile_picture.filename

    def test_large_but_valid_file_upload(self, client, auth_user):
        """Test uploading a file just under the size limit"""
        # Create a file just under 5MB (5MB = 5242880 bytes)
        large_but_valid_content = b'x' * (5 * 1024 * 1024 - 1000)  # Just under 5MB
        
        response = client.post('/profile/picture/upload', data={
            'profile_picture': (io.BytesIO(large_but_valid_content), 'large_valid.jpg')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Profile picture uploaded successfully!' in response.data
        
        # Verify the file was uploaded
        profile_picture = Attachment.query.filter_by(
            user_id=auth_user.id,
            type='profile_picture'
        ).first()
        assert profile_picture is not None
        assert profile_picture.filename == 'large_valid.jpg'
