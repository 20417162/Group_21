import pytest
import base64
from datetime import datetime, date
from app import create_app, db
from app.models import User, AikidoInformation, Attachment, TrainingAttendance, ProofOfPayment
from flask import url_for


class TestAdminUserProfile:
    """Test admin user profile functionality"""

    def test_admin_can_access_user_profile_page(self, client, admin_user, regular_user):
        """Test that admin users can access user profile pages"""
        # Login as admin
        response = client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })
        assert response.status_code == 302

        # Access user profile page
        response = client.get(f'/admin/user/{regular_user.id}')
        assert response.status_code == 200
        assert b'User Profile' in response.data
        assert b'Admin View' in response.data
        assert regular_user.first_name.encode() in response.data
        assert regular_user.surname.encode() in response.data

    def test_non_admin_cannot_access_user_profile_page(self, client, regular_user, another_user):
        """Test that non-admin users cannot access user profile pages"""
        # Login as regular user
        response = client.post('/login', data={
            'username': regular_user.username,
            'password': 'user123'
        })
        assert response.status_code == 302

        # Try to access another user's profile page
        response = client.get(f'/admin/user/{another_user.id}')
        assert response.status_code == 302  # Should redirect
        
        # Follow redirect and check for permission denied message
        response = client.get(f'/admin/user/{another_user.id}', follow_redirects=True)
        assert b'You do not have permission to access this page' in response.data

    def test_unauthenticated_user_cannot_access_user_profile_page(self, client, regular_user):
        """Test that unauthenticated users cannot access user profile pages"""
        response = client.get(f'/admin/user/{regular_user.id}')
        assert response.status_code == 302  # Should redirect
        
        # Follow redirect and check that we're redirected to login/home page
        response = client.get(f'/admin/user/{regular_user.id}', follow_redirects=True)
        # Should be redirected to home page (since that's where admin_required redirects to)
        assert response.status_code == 200
        assert b'Aikido' in response.data  # Should be on home page

    def test_admin_can_view_all_user_information(self, client, admin_user, regular_user_with_data):
        """Test that admin can view all user information including aikido info and training"""
        user, aikido_info, training_session = regular_user_with_data
        
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Access user profile page
        response = client.get(f'/admin/user/{user.id}')
        assert response.status_code == 200
        
        # Check user basic info
        assert user.first_name.encode() in response.data
        assert user.surname.encode() in response.data
        assert user.username.encode() in response.data
        
        # Check aikido info
        assert aikido_info.aikido_type.encode() in response.data
        assert aikido_info.aikido_rank.encode() in response.data
        assert aikido_info.certificate_no.encode() in response.data
        
        # Check training session
        assert str(training_session.hours).encode() in response.data

    def test_admin_can_download_unverified_proof_of_payment(self, client, admin_user, regular_user_with_proof_of_payment):
        """Test that admin can download unverified proof of payments"""
        user, pop, attachment = regular_user_with_proof_of_payment
        
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Download proof of payment
        response = client.get(f'/admin/user/{user.id}/pop/{pop.id}/download')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'image/png'
        assert 'admin_pop_' in response.headers['Content-Disposition']

    def test_admin_can_verify_proof_of_payment(self, client, admin_user, regular_user_with_proof_of_payment):
        """Test that admin can verify proof of payment"""
        user, pop, attachment = regular_user_with_proof_of_payment
        
        # Ensure payment is not verified initially
        assert pop.admin_verified is False
        
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Verify proof of payment
        response = client.post(f'/admin/user/{user.id}/pop/{pop.id}/verify')
        assert response.status_code == 302  # Should redirect back to user profile
        
        # Check that payment is now verified in database
        db.session.refresh(pop)
        assert pop.admin_verified is True

    def test_verified_status_persists_after_verification(self, client, admin_user, regular_user_with_proof_of_payment):
        """Test that verified status persists and is visible"""
        user, pop, attachment = regular_user_with_proof_of_payment
        
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Verify proof of payment
        client.post(f'/admin/user/{user.id}/pop/{pop.id}/verify')
        
        # Check user profile page shows verified status
        response = client.get(f'/admin/user/{user.id}')
        assert response.status_code == 200
        assert b'Verified' in response.data
        assert b'badge bg-success' in response.data  # Green verified badge

    def test_admin_cannot_verify_already_verified_payment(self, client, admin_user, regular_user_with_verified_proof_of_payment):
        """Test that admin cannot verify an already verified payment"""
        user, pop, attachment = regular_user_with_verified_proof_of_payment
        
        # Ensure payment is verified
        assert pop.admin_verified is True
        
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Check user profile page doesn't show verify button for this specific payment
        response = client.get(f'/admin/user/{user.id}')
        assert response.status_code == 200
        # Check that the specific verify button with this payment ID is not present
        verify_button_pattern = f'onclick="confirmVerify({pop.id},'
        assert verify_button_pattern.encode() not in response.data
        
        # Try to verify already verified payment
        response = client.post(f'/admin/user/{user.id}/pop/{pop.id}/verify', follow_redirects=True)
        assert b'already verified' in response.data

    def test_admin_can_download_user_certificate(self, client, admin_user, regular_user_with_certificate):
        """Test that admin can download user's aikido certificate"""
        user, certificate = regular_user_with_certificate
        
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Download certificate
        response = client.get(f'/admin/user/{user.id}/certificate/download')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
        assert 'admin_certificate_' in response.headers['Content-Disposition']
        assert certificate.filename in response.headers['Content-Disposition']

    def test_admin_user_profile_shows_no_certificate_message(self, client, admin_user, regular_user):
        """Test that admin user profile shows appropriate message when user has no aikido credentials"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Access user profile page
        response = client.get(f'/admin/user/{regular_user.id}')
        assert response.status_code == 200
        # Since the user has no aikido_info at all, it should show the no credentials message
        assert b'User has not provided Aikido credentials yet' in response.data

    def test_admin_user_profile_shows_no_training_message(self, client, admin_user, regular_user):
        """Test that admin user profile shows appropriate message when user has no training sessions"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Access user profile page
        response = client.get(f'/admin/user/{regular_user.id}')
        assert response.status_code == 200
        assert b'User has not recorded any training sessions yet' in response.data

    def test_admin_user_profile_shows_no_payments_message(self, client, admin_user, regular_user):
        """Test that admin user profile shows appropriate message when user has no proof of payments"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Access user profile page
        response = client.get(f'/admin/user/{regular_user.id}')
        assert response.status_code == 200
        assert b'User has not uploaded any proof of payments yet' in response.data

    def test_admin_user_profile_shows_admin_badge_for_admin_user(self, client, admin_user, another_admin_user):
        """Test that admin user profile shows admin badge when viewing another admin user"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Access admin user profile page
        response = client.get(f'/admin/user/{another_admin_user.id}')
        assert response.status_code == 200
        assert b'Administrator' in response.data
        assert b'badge bg-danger' in response.data  # Red admin badge

    def test_back_to_dashboard_button_works(self, client, admin_user, regular_user):
        """Test that the back to dashboard button works correctly"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Access user profile page
        response = client.get(f'/admin/user/{regular_user.id}')
        assert response.status_code == 200
        assert b'Back to Dashboard' in response.data
        assert f'href="{url_for("main.admin_dashboard")}"'.encode() in response.data

    def test_nonexistent_user_profile_returns_404(self, client, admin_user):
        """Test that accessing a non-existent user profile returns 404"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Try to access non-existent user profile
        response = client.get('/admin/user/99999')
        assert response.status_code == 404

    def test_download_nonexistent_proof_of_payment_redirects_with_error(self, client, admin_user, regular_user):
        """Test that attempting to download non-existent proof of payment redirects with error"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Try to download non-existent proof of payment
        response = client.get(f'/admin/user/{regular_user.id}/pop/99999/download', follow_redirects=True)
        assert b'Proof of payment not found' in response.data

    def test_download_nonexistent_certificate_redirects_with_error(self, client, admin_user, regular_user):
        """Test that attempting to download non-existent certificate redirects with error"""
        # Login as admin
        client.post('/login', data={
            'username': admin_user.username,
            'password': 'admin123'
        })

        # Try to download non-existent certificate
        response = client.get(f'/admin/user/{regular_user.id}/certificate/download', follow_redirects=True)
        assert b'No certificate found for this user' in response.data
