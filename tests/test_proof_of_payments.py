
import pytest
import base64
from datetime import datetime
from flask_login import login_user
from app import create_app, db
from app.models import User, ProofOfPayment, Attachment
from .conftest import create_test_user


@pytest.fixture
def app():
    app = create_app('testing')
    
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


class TestProofOfPaymentsUpload:
    def test_upload_proof_of_payment_success(self, client, auth_user, app):
        """Test successful proof of payment upload"""
        # Create a test file using BytesIO to simulate a real file upload
        from io import BytesIO
        
        test_file_data = b'fake pdf content'
        test_file = (BytesIO(test_file_data), 'test_payment.pdf')
        
        # Upload proof of payment (creates its own request context)
        response = client.post('/profile/pop/upload', data={
            'proof_of_payment': test_file,
            'month_year': 'January 2025'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 302  # Redirect after upload
        
        # Verify proof of payment was created (need to query within app context)
        with app.app_context():
            # Get the user by username to ensure we have the correct ID in this context
            user = User.query.filter_by(username='testuser').first()
            assert user is not None
            
            pop = ProofOfPayment.query.filter_by(user_id=user.id).first()
            assert pop is not None
            assert pop.month_year == 'January 2025'
            assert pop.admin_verified == False
            
            # Verify attachment was created
            attachment = Attachment.query.filter_by(id=pop.attachment_id).first()
            assert attachment is not None
            assert attachment.type == 'pop'
            assert attachment.filename == 'test_payment.pdf'

    def test_upload_proof_of_payment_no_file(self, client, app):
        """Test upload with no file selected"""
        # Create user in app context and commit
        user_id = create_test_user(app)
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Try to upload without file
        response = client.post('/profile/pop/upload', data={
            'month_year': 'January 2025'
        })
        
        assert response.status_code == 302
        
        # Verify no proof of payment was created
        with app.app_context():
            pop = ProofOfPayment.query.filter_by(user_id=user_id).first()
            assert pop is None

    def test_upload_proof_of_payment_no_month_year(self, client, app):
        """Test upload with no month/year specified"""
        # Create user in app context and commit
        user_id = create_test_user(app)
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        test_file_data = b'fake pdf content'
        
        # Try to upload without month/year
        response = client.post('/profile/pop/upload', data={
            'proof_of_payment': (test_file_data, 'test_payment.pdf', 'application/pdf')
        }, content_type='multipart/form-data')
        
        assert response.status_code == 302
        
        # Verify no proof of payment was created
        with app.app_context():
            pop = ProofOfPayment.query.filter_by(user_id=user_id).first()
            assert pop is None

    def test_upload_duplicate_month_year(self, client, app):
        """Test uploading proof of payment for existing month/year"""
        # Create user in app context and commit
        user_id = create_test_user(app)
        
        # Create existing proof of payment
        with app.app_context():
            test_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='existing_payment.pdf',
                data=base64.b64encode(b'existing content').decode('utf-8')
            )
            db.session.add(test_attachment)
            db.session.flush()
            
            existing_pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=test_attachment.id,
                month_year='January 2025',
                admin_verified=False
            )
            db.session.add(existing_pop)
            db.session.commit()
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        test_file_data = b'new pdf content'
        
        # Try to upload for same month/year
        response = client.post('/profile/pop/upload', data={
            'proof_of_payment': (test_file_data, 'new_payment.pdf', 'application/pdf'),
            'month_year': 'January 2025'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 302
        
        # Verify only one proof of payment exists
        with app.app_context():
            pops = ProofOfPayment.query.filter_by(user_id=user_id, month_year='January 2025').all()
            assert len(pops) == 1

    def test_upload_invalid_file_type(self, client, app):
        """Test upload with invalid file type"""
        # Create user in app context and commit
        user_id = create_test_user(app)
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        test_file_data = b'fake text content'
        
        # Try to upload text file
        response = client.post('/profile/pop/upload', data={
            'proof_of_payment': (test_file_data, 'test_payment.txt', 'text/plain'),
            'month_year': 'January 2025'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 302
        
        # Verify no proof of payment was created
        with app.app_context():
            pop = ProofOfPayment.query.filter_by(user_id=user_id).first()
            assert pop is None


class TestProofOfPaymentsView:
    def test_view_proof_of_payment_success(self, client, app):
        """Test viewing/downloading proof of payment"""
        # Create user and proof of payment
        user_id = create_test_user(app)
        
        pop_id = None
        with app.app_context():
            # Create proof of payment
            test_content = b'fake pdf content'
            test_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='test_payment.pdf',
                data=base64.b64encode(test_content).decode('utf-8')
            )
            db.session.add(test_attachment)
            db.session.flush()
            
            pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=test_attachment.id,
                month_year='January 2025',
                admin_verified=False
            )
            db.session.add(pop)
            db.session.commit()
            pop_id = pop.id
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # View proof of payment
        response = client.get(f'/profile/pop/view/{pop_id}')
        
        assert response.status_code == 200
        assert response.data == test_content
        assert 'pop_January 2025_test_payment.pdf' in response.headers['Content-Disposition']

    def test_view_proof_of_payment_not_found(self, client, app):
        """Test viewing non-existent proof of payment"""
        # Create user
        create_test_user(app)
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Try to view non-existent proof of payment
        response = client.get('/profile/pop/view/999')
        
        assert response.status_code == 302  # Redirect to profile

    def test_view_proof_of_payment_wrong_user(self, client, app):
        """Test viewing another user's proof of payment"""
        # Create two users and proof of payment
        pop_id = None
        with app.app_context():
            user1 = User(first_name='User', surname='One', username='user1')
            user1.set_password('password123')
            user2 = User(first_name='User', surname='Two', username='user2')
            user2.set_password('password123')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Create proof of payment for user1
            test_attachment = Attachment(
                user_id=user1.id,
                type='pop',
                filename='user1_payment.pdf',
                data=base64.b64encode(b'user1 content').decode('utf-8')
            )
            db.session.add(test_attachment)
            db.session.flush()
            
            pop = ProofOfPayment(
                user_id=user1.id,
                attachment_id=test_attachment.id,
                month_year='January 2025',
                admin_verified=False
            )
            db.session.add(pop)
            db.session.commit()
            pop_id = pop.id
        
        # Login as user2
        client.post('/login', data={
            'username': 'user2',
            'password': 'password123'
        })
        
        # Try to view user1's proof of payment
        response = client.get(f'/profile/pop/view/{pop_id}')
        
        assert response.status_code == 302  # Redirect to profile


class TestProofOfPaymentsDelete:
    def test_delete_unverified_proof_of_payment(self, client, app):
        """Test deleting unverified proof of payment"""
        # Create user and proof of payment
        user_id = create_test_user(app)
        
        pop_id = None
        attachment_id = None
        with app.app_context():
            # Create unverified proof of payment
            test_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='test_payment.pdf',
                data=base64.b64encode(b'test content').decode('utf-8')
            )
            db.session.add(test_attachment)
            db.session.flush()
            
            pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=test_attachment.id,
                month_year='January 2025',
                admin_verified=False
            )
            db.session.add(pop)
            db.session.commit()
            
            pop_id = pop.id
            attachment_id = test_attachment.id
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Delete proof of payment
        response = client.post(f'/profile/pop/delete/{pop_id}')
        
        assert response.status_code == 302  # Redirect to profile
        
        # Verify both proof of payment and attachment were deleted
        with app.app_context():
            assert ProofOfPayment.query.get(pop_id) is None
            assert Attachment.query.get(attachment_id) is None

    def test_delete_verified_proof_of_payment_forbidden(self, client, app):
        """Test that verified proof of payments cannot be deleted"""
        # Create user and proof of payment
        user_id = create_test_user(app)
        
        pop_id = None
        with app.app_context():
            # Create verified proof of payment
            test_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='verified_payment.pdf',
                data=base64.b64encode(b'verified content').decode('utf-8')
            )
            db.session.add(test_attachment)
            db.session.flush()
            
            pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=test_attachment.id,
                month_year='January 2025',
                admin_verified=True  # Verified!
            )
            db.session.add(pop)
            db.session.commit()
            
            pop_id = pop.id
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Try to delete verified proof of payment
        response = client.post(f'/profile/pop/delete/{pop_id}')
        
        assert response.status_code == 302  # Redirect to profile
        
        # Verify proof of payment still exists
        with app.app_context():
            assert ProofOfPayment.query.get(pop_id) is not None

    def test_delete_proof_of_payment_wrong_user(self, client, app):
        """Test deleting another user's proof of payment"""
        # Create two users and proof of payment
        pop_id = None
        with app.app_context():
            user1 = User(first_name='User', surname='One', username='user1')
            user1.set_password('password123')
            user2 = User(first_name='User', surname='Two', username='user2')
            user2.set_password('password123')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Create proof of payment for user1
            test_attachment = Attachment(
                user_id=user1.id,
                type='pop',
                filename='user1_payment.pdf',
                data=base64.b64encode(b'user1 content').decode('utf-8')
            )
            db.session.add(test_attachment)
            db.session.flush()
            
            pop = ProofOfPayment(
                user_id=user1.id,
                attachment_id=test_attachment.id,
                month_year='January 2025',
                admin_verified=False
            )
            db.session.add(pop)
            db.session.commit()
            
            pop_id = pop.id
        
        # Login as user2
        client.post('/login', data={
            'username': 'user2',
            'password': 'password123'
        })
        
        # Try to delete user1's proof of payment
        response = client.post(f'/profile/pop/delete/{pop_id}')
        
        assert response.status_code == 302  # Redirect to profile
        
        # Verify proof of payment still exists
        with app.app_context():
            assert ProofOfPayment.query.get(pop_id) is not None


class TestProofOfPaymentsProfileDisplay:
    def test_profile_displays_latest_six_pops(self, client, app):
        """Test that profile displays only the latest 6 proof of payments"""
        # Create user and proof of payments
        user_id = create_test_user(app)
        
        with app.app_context():
            # Create 8 proof of payments
            for i in range(8):
                test_attachment = Attachment(
                    user_id=user_id,
                    type='pop',
                    filename=f'payment_{i+1}.pdf',
                    data=base64.b64encode(f'content {i+1}'.encode()).decode('utf-8')
                )
                db.session.add(test_attachment)
                db.session.flush()
                
                pop = ProofOfPayment(
                    user_id=user_id,
                    attachment_id=test_attachment.id,
                    month_year=f'Month {i+1} 2025',
                    admin_verified=i % 2 == 0  # Alternate verified/unverified
                )
                db.session.add(pop)
            
            db.session.commit()
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # View profile
        response = client.get('/profile')
        
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        
        # Should show latest 6 payments (Month 8, 7, 6, 5, 4, 3)
        for i in [8, 7, 6, 5, 4, 3]:
            assert f'Month {i} 2025' in response_text
        
        # Should not show oldest 2 payments (Month 2, 1)
        for i in [2, 1]:
            assert f'Month {i} 2025' not in response_text

    def test_profile_shows_correct_border_colors(self, client, app):
        """Test that proof of payments show correct border colors based on verification status"""
        # Create user and proof of payments
        user_id = create_test_user(app)
        
        with app.app_context():
            # Create verified proof of payment
            verified_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='verified_payment.pdf',
                data=base64.b64encode(b'verified content').decode('utf-8')
            )
            db.session.add(verified_attachment)
            db.session.flush()
            
            verified_pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=verified_attachment.id,
                month_year='January 2025',
                admin_verified=True
            )
            db.session.add(verified_pop)
            
            # Create unverified proof of payment
            unverified_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='unverified_payment.pdf',
                data=base64.b64encode(b'unverified content').decode('utf-8')
            )
            db.session.add(unverified_attachment)
            db.session.flush()
            
            unverified_pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=unverified_attachment.id,
                month_year='February 2025',
                admin_verified=False
            )
            db.session.add(unverified_pop)
            db.session.commit()
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # View profile
        response = client.get('/profile')
        
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        
        # Verify verified payment shows green border and verified badge
        assert 'border-success' in response_text
        assert 'Verified' in response_text
        
        # Verify unverified payment shows yellow/warning border and pending badge
        assert 'border-warning' in response_text
        assert 'Pending' in response_text

    def test_profile_shows_delete_button_only_for_unverified(self, client, app):
        """Test that delete button only appears for unverified proof of payments"""
        # Create user and proof of payments
        user_id = create_test_user(app)
        
        with app.app_context():
            # Create verified proof of payment
            verified_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='verified_payment.pdf',
                data=base64.b64encode(b'verified content').decode('utf-8')
            )
            db.session.add(verified_attachment)
            db.session.flush()
            
            verified_pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=verified_attachment.id,
                month_year='January 2025',
                admin_verified=True
            )
            db.session.add(verified_pop)
            
            # Create unverified proof of payment
            unverified_attachment = Attachment(
                user_id=user_id,
                type='pop',
                filename='unverified_payment.pdf',
                data=base64.b64encode(b'unverified content').decode('utf-8')
            )
            db.session.add(unverified_attachment)
            db.session.flush()
            
            unverified_pop = ProofOfPayment(
                user_id=user_id,
                attachment_id=unverified_attachment.id,
                month_year='February 2025',
                admin_verified=False
            )
            db.session.add(unverified_pop)
            db.session.commit()
            
            # Debug: verify the boolean values are stored correctly
            stored_verified_pop = ProofOfPayment.query.filter_by(month_year='January 2025').first()
            stored_unverified_pop = ProofOfPayment.query.filter_by(month_year='February 2025').first()
            
            # Ensure boolean values are correct
            assert stored_verified_pop.admin_verified is True
            assert stored_unverified_pop.admin_verified is False
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # View profile
        response = client.get('/profile')
        
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        
        # Debug: Print the relevant sections of the HTML
        import re
        # Find all proof of payment sections
        pop_sections = re.findall(r'<div class="col-12 col-md-6 col-lg-4 mb-3".*?</div>\s*</div>\s*</div>', response_text, re.DOTALL)
        print(f"Found {len(pop_sections)} POP sections")
        
        for i, section in enumerate(pop_sections):
            has_delete = 'confirmDeletePop' in section
            is_verified = 'Verified' in section
            is_pending = 'Pending' in section
            print(f"Section {i+1}: Verified={is_verified}, Pending={is_pending}, Has Delete Button={has_delete}")
            if 'January 2025' in section:
                print(f"January section: {section[:200]}")
        
        # Count delete buttons more specifically - count onclick occurrences only
        delete_button_count = response_text.count('onclick="confirmDeletePop')
        print(f"Delete button count (onclick only): {delete_button_count}")
        assert delete_button_count == 1

    def test_profile_no_pops_shows_info_message(self, client, app):
        """Test that profile shows info message when no proof of payments exist"""
        # Create user
        create_test_user(app)
        
        # Login user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # View profile (no proof of payments created)
        response = client.get('/profile')
        
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        
        assert 'No proof of payments uploaded yet' in response_text


class TestProofOfPaymentsAuthentication:
    def test_upload_requires_login(self, client, app):
        """Test that upload endpoint requires authentication"""
        test_file_data = b'fake pdf content'
        
        response = client.post('/profile/pop/upload', data={
            'proof_of_payment': (test_file_data, 'test_payment.pdf', 'application/pdf'),
            'month_year': 'January 2025'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 401 or response.status_code == 302  # Unauthorized or redirect to login

    def test_view_requires_login(self, client, app):
        """Test that view endpoint requires authentication"""
        response = client.get('/profile/pop/view/1')
        
        assert response.status_code == 401 or response.status_code == 302  # Unauthorized or redirect to login

    def test_delete_requires_login(self, client, app):
        """Test that delete endpoint requires authentication"""
        response = client.post('/profile/pop/delete/1')
        
        assert response.status_code == 401 or response.status_code == 302  # Unauthorized or redirect to login
