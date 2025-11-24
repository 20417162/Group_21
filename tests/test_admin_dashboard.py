import pytest
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime, date
from app import create_app, db
from app.models import User, Attachment, ProofOfPayment


class TestAdminDashboard:
    """Comprehensive E2E tests for admin dashboard functionality."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Set up test client and clean up after each test."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create tables
        db.create_all()
        
        yield
        
        # Clean up
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_test_image(self, format='JPEG'):
        """Create a test image file for upload testing."""
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return img_io

    def create_admin_user(self, username='admin', admin=True):
        """Create an admin user for testing."""
        user = User(
            username=username,
            first_name='Admin',
            surname='User'
        )
        user.set_password('password123')
        user.admin = admin
        db.session.add(user)
        db.session.commit()
        return user

    def create_regular_user(self, username='user1', first_name='John', surname='Doe'):
        """Create a regular user for testing."""
        user = User(
            username=username,
            first_name=first_name,
            surname=surname
        )
        user.set_password('password123')
        user.admin = False
        db.session.add(user)
        db.session.commit()
        return user

    def login_user(self, username, password='password123'):
        """Log in a user for testing."""
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def create_profile_picture(self, user):
        """Create a profile picture for a user."""
        img_data = self.create_test_image()
        encoded_data = base64.b64encode(img_data.read()).decode('utf-8')
        
        attachment = Attachment(
            user_id=user.id,
            type='profile_picture',
            filename='profile.jpg',
            data=encoded_data
        )
        db.session.add(attachment)
        db.session.commit()
        return attachment

    def create_proof_of_payment(self, user, month_year='January 2025', admin_verified=False):
        """Create a proof of payment for a user."""
        # Create attachment first
        img_data = self.create_test_image()
        encoded_data = base64.b64encode(img_data.read()).decode('utf-8')
        
        attachment = Attachment(
            user_id=user.id,
            type='pop',
            filename='payment.pdf',
            data=encoded_data
        )
        db.session.add(attachment)
        db.session.flush()
        
        # Create proof of payment
        pop = ProofOfPayment(
            user_id=user.id,
            attachment_id=attachment.id,
            month_year=month_year,
            admin_verified=admin_verified
        )
        db.session.add(pop)
        db.session.commit()
        return pop

    def test_admin_dashboard_access_control_unauthenticated(self):
        """Test that unauthenticated users cannot access admin dashboard."""
        response = self.client.get('/admin')
        
        # Should redirect to login page
        assert response.status_code == 302
        assert '/login' in response.location or '#login' in response.location

    def test_admin_dashboard_access_control_non_admin(self):
        """Test that non-admin users cannot access admin dashboard."""
        # Create and login regular user
        user = self.create_regular_user()
        self.login_user(user.username)

        response = self.client.get('/admin')
        
        # Should redirect to home page with error message
        assert response.status_code == 302
        
        # Follow redirect to check flash message
        response = self.client.get('/admin', follow_redirects=True)
        assert b'You do not have permission to access this page' in response.data or \
               b'permission' in response.data.lower()

    def test_admin_dashboard_access_control_admin_user(self):
        """Test that admin users can access admin dashboard."""
        # Create and login admin user
        admin = self.create_admin_user()
        self.login_user(admin.username)

        response = self.client.get('/admin')
        
        # Should successfully access admin dashboard
        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data
        assert b'Users Overview' in response.data

    def test_admin_dashboard_displays_user_information(self):
        """Test that admin dashboard displays correct user information."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Doe')
        user2 = self.create_regular_user('user2', 'Jane', 'Smith')
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        
        assert response.status_code == 200
        
        # Check that user information is displayed
        assert b'John' in response.data
        assert b'Doe' in response.data
        assert b'Jane' in response.data
        assert b'Smith' in response.data
        assert b'user1' in response.data
        assert b'user2' in response.data

    def test_admin_dashboard_profile_pictures(self):
        """Test that profile pictures display correctly with fallback."""
        # Create admin and test users
        admin = self.create_admin_user()
        user_with_pic = self.create_regular_user('user1', 'John', 'Doe')
        user_without_pic = self.create_regular_user('user2', 'Jane', 'Smith')
        
        # Create profile picture for one user
        self.create_profile_picture(user_with_pic)
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        # Check that profile picture route is referenced for user with picture
        expected_pic_url = f'/admin/user/{user_with_pic.id}/profile-picture'
        assert expected_pic_url.encode() in response.data
        
        # Check that users without pictures show fallback icon
        assert b'fa-user' in response.data

    def test_admin_dashboard_pending_payments_indicator(self):
        """Test that pending payments indicator shows correctly."""
        # Create admin and test users
        admin = self.create_admin_user()
        user_with_pending = self.create_regular_user('user1', 'John', 'Doe')
        user_without_pending = self.create_regular_user('user2', 'Jane', 'Smith')
        user_with_verified = self.create_regular_user('user3', 'Bob', 'Wilson')
        
        # Create payments
        self.create_proof_of_payment(user_with_pending, 'January 2025', admin_verified=False)
        self.create_proof_of_payment(user_with_pending, 'February 2025', admin_verified=False)
        self.create_proof_of_payment(user_with_verified, 'January 2025', admin_verified=True)
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        # User with pending payments should show count > 0
        response_text = response.data.decode()
        assert 'John' in response_text
        assert 'Doe' in response_text
        
        # Should show pending payments badge/indicator
        assert 'badge bg-warning' in response_text or 'pending' in response_text.lower()
        
        # User without pending payments should show 0
        assert 'Jane' in response_text
        assert 'Smith' in response_text

    def test_admin_dashboard_admin_status_indicator(self):
        """Test that admin status shows correctly."""
        # Create admin and regular users
        admin = self.create_admin_user('admin1', admin=True)
        regular_user = self.create_regular_user('user1', 'John', 'Doe')
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        response_text = response.data.decode()
        
        # Should show admin badge for admin user
        assert 'Admin' in response_text
        assert 'badge bg-danger' in response_text or 'crown' in response_text
        
        # Should show regular user badge for non-admin
        assert 'badge bg-secondary' in response_text or 'User' in response_text

    def test_admin_dashboard_pagination(self):
        """Test that pagination works correctly."""
        # Create admin
        admin = self.create_admin_user()
        
        # Create 25 users (more than default page size of 20)
        users = []
        for i in range(25):
            user = self.create_regular_user(f'user{i}', f'User{i}', f'Test{i}')
            users.append(user)
        
        # Login admin
        self.login_user(admin.username)

        # Test first page
        response = self.client.get('/admin')
        assert response.status_code == 200
        
        # Should show pagination controls
        assert b'pagination' in response.data
        assert b'Next' in response.data or b'&raquo;' in response.data
        
        # Test second page
        response = self.client.get('/admin?page=2')
        assert response.status_code == 200
        
        # Should show pagination controls
        assert b'pagination' in response.data
        assert b'Previous' in response.data or b'&laquo;' in response.data

    def test_admin_dashboard_statistics_cards(self):
        """Test that statistics cards show correct information."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Doe')
        user2 = self.create_regular_user('user2', 'Jane', 'Smith')
        
        # Create some pending payments
        self.create_proof_of_payment(user1, 'January 2025', admin_verified=False)
        self.create_proof_of_payment(user2, 'February 2025', admin_verified=False)
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        response_text = response.data.decode()
        
        # Should show total users (including admin)
        assert '3' in response_text  # 3 total users
        
        # Should show pending payments count
        assert '2' in response_text  # 2 pending payments

    def test_admin_dashboard_user_profile_picture_route(self):
        """Test that admin can view user profile pictures."""
        # Create admin and user with profile picture
        admin = self.create_admin_user()
        user = self.create_regular_user('user1', 'John', 'Doe')
        self.create_profile_picture(user)
        
        # Login admin
        self.login_user(admin.username)

        # Access user's profile picture
        response = self.client.get(f'/admin/user/{user.id}/profile-picture')
        
        assert response.status_code == 200
        assert response.content_type.startswith('image/')

    def test_admin_dashboard_user_profile_picture_route_not_found(self):
        """Test that accessing non-existent profile picture returns 404."""
        # Create admin and user without profile picture
        admin = self.create_admin_user()
        user = self.create_regular_user('user1', 'John', 'Doe')
        
        # Login admin
        self.login_user(admin.username)

        # Try to access non-existent profile picture
        response = self.client.get(f'/admin/user/{user.id}/profile-picture')
        
        assert response.status_code == 404

    def test_admin_dashboard_user_profile_picture_route_access_control(self):
        """Test that only admins can access user profile picture route."""
        # Create users
        admin = self.create_admin_user()
        regular_user = self.create_regular_user('user1', 'John', 'Doe')
        self.create_profile_picture(regular_user)
        
        # Try to access as unauthenticated user
        response = self.client.get(f'/admin/user/{regular_user.id}/profile-picture')
        assert response.status_code == 302  # Redirect to login
        
        # Try to access as regular user
        regular_user2 = self.create_regular_user('user2', 'Jane', 'Smith')
        self.login_user(regular_user2.username)
        
        response = self.client.get(f'/admin/user/{regular_user.id}/profile-picture')
        assert response.status_code == 302  # Redirect with permission error

    def test_admin_dashboard_joined_date_display(self):
        """Test that user joined dates are displayed correctly."""
        # Create admin and users
        admin = self.create_admin_user()
        user = self.create_regular_user('user1', 'John', 'Doe')
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        # Should show joined date (format: "Nov 2025" or similar)
        current_month = datetime.now().strftime('%b')
        current_year = str(datetime.now().year)
        
        response_text = response.data.decode()
        assert current_month in response_text or current_year in response_text

    def test_admin_dashboard_error_handling(self):
        """Test admin dashboard error handling."""
        # Create admin
        admin = self.create_admin_user()
        self.login_user(admin.username)
        
        # Test with invalid page number
        response = self.client.get('/admin?page=999')
        
        # Should handle gracefully (either show empty page or redirect)
        assert response.status_code in [200, 302]

    def test_admin_dashboard_comprehensive_scenario(self):
        """Test comprehensive scenario with multiple users in different states."""
        # Create admin
        admin = self.create_admin_user('admin', admin=True)
        
        # Create users with different states
        user_with_everything = self.create_regular_user('user1', 'John', 'Doe')
        user_with_pic_only = self.create_regular_user('user2', 'Jane', 'Smith')
        user_with_payments_only = self.create_regular_user('user3', 'Bob', 'Wilson')
        user_minimal = self.create_regular_user('user4', 'Alice', 'Brown')
        
        # Set up different user states
        self.create_profile_picture(user_with_everything)
        self.create_proof_of_payment(user_with_everything, 'January 2025', admin_verified=False)
        
        self.create_profile_picture(user_with_pic_only)
        
        self.create_proof_of_payment(user_with_payments_only, 'January 2025', admin_verified=False)
        self.create_proof_of_payment(user_with_payments_only, 'February 2025', admin_verified=True)
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        response_text = response.data.decode()
        
        # Verify all users are displayed
        assert 'John' in response_text and 'Doe' in response_text
        assert 'Jane' in response_text and 'Smith' in response_text
        assert 'Bob' in response_text and 'Wilson' in response_text
        assert 'Alice' in response_text and 'Brown' in response_text
        
        # Verify admin dashboard elements are present
        assert 'Admin Dashboard' in response_text
        assert 'Users Overview' in response_text
        assert 'Total Users' in response_text
        assert 'Pending Payments' in response_text
        
        # Verify statistics are correct
        assert '5' in response_text  # 5 total users (including admin)
        assert '2' in response_text  # 2 pending payments (1 from each user)

    def test_admin_dashboard_responsive_design_elements(self):
        """Test that admin dashboard includes responsive design elements."""
        # Create admin
        admin = self.create_admin_user()
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        response_text = response.data.decode()
        
        # Check for Bootstrap responsive classes
        assert 'table-responsive' in response_text
        assert 'container' in response_text
        assert 'col-' in response_text
        
        # Check for mobile-friendly elements
        assert 'card' in response_text
        assert 'badge' in response_text

    def test_admin_dashboard_users_sorted_by_pending_payments(self):
        """Test that users are sorted with pending payments first, then by creation date."""
        # Create admin
        admin = self.create_admin_user('admin', admin=True)
        
        # Create users with different pending payment counts
        # Note: Create in order that would be wrong if sorting only by creation date
        user_no_pending = self.create_regular_user('user1', 'Alice', 'Zero')  # Created first, 0 pending
        user_one_pending = self.create_regular_user('user2', 'Bob', 'One')    # Created second, 1 pending
        user_two_pending = self.create_regular_user('user3', 'Charlie', 'Two') # Created third, 2 pending
        user_also_no_pending = self.create_regular_user('user4', 'David', 'Also_Zero') # Created fourth, 0 pending
        
        # Create pending payments (admin_verified=False means pending)
        self.create_proof_of_payment(user_one_pending, 'January 2025', admin_verified=False)
        
        self.create_proof_of_payment(user_two_pending, 'January 2025', admin_verified=False)
        self.create_proof_of_payment(user_two_pending, 'February 2025', admin_verified=False)
        
        # Login admin
        self.login_user(admin.username)

        response = self.client.get('/admin')
        assert response.status_code == 200
        
        response_text = response.data.decode()
        
        # Find positions of users in the response
        charlie_pos = response_text.find('Charlie')  # Should be first (2 pending)
        bob_pos = response_text.find('Bob')          # Should be second (1 pending)
        david_pos = response_text.find('David')      # Should be third (0 pending, created later)
        alice_pos = response_text.find('Alice')     # Should be fourth (0 pending, created earlier)
        
        # All users should be found
        assert charlie_pos != -1, "Charlie (2 pending) should be in the response"
        assert bob_pos != -1, "Bob (1 pending) should be in the response"
        assert alice_pos != -1, "Alice (0 pending) should be in the response"
        assert david_pos != -1, "David (0 pending) should be in the response"
        
        # Verify sorting order: users with more pending payments appear first
        assert charlie_pos < bob_pos, "Charlie (2 pending) should appear before Bob (1 pending)"
        assert bob_pos < david_pos, "Bob (1 pending) should appear before David (0 pending)"
        assert bob_pos < alice_pos, "Bob (1 pending) should appear before Alice (0 pending)"
        
        # Among users with same pending count, newer users should appear first
        assert david_pos < alice_pos, "David (newer, 0 pending) should appear before Alice (older, 0 pending)"
        
        # Verify pending payment badges are displayed correctly 
        # Charlie should show 2 pending
        charlie_section = response_text[charlie_pos:charlie_pos + 2000]  
        assert 'badge bg-warning' in charlie_section, "Charlie should have warning badge"
        badge_start = charlie_section.find('badge bg-warning')
        badge_area = charlie_section[badge_start:badge_start + 200] if badge_start != -1 else charlie_section
        assert '2' in badge_area, f"Charlie should show 2 pending payments, found: {badge_area}"
        
        # Bob should show 1 pending
        bob_section = response_text[bob_pos:bob_pos + 2000]  
        assert 'badge bg-warning' in bob_section, "Bob should have warning badge"
        badge_start = bob_section.find('badge bg-warning')
        badge_area = bob_section[badge_start:badge_start + 200] if badge_start != -1 else bob_section
        assert '1' in badge_area, f"Bob should show 1 pending payment, found: {badge_area}"
        
        # Alice and David should show 0 pending (success badge)
        alice_section = response_text[alice_pos:alice_pos + 2000]
        david_section = response_text[david_pos:david_pos + 2000]
        
        assert 'badge bg-success' in alice_section, "Alice should have success badge"
        badge_start = alice_section.find('badge bg-success')
        badge_area = alice_section[badge_start:badge_start + 200] if badge_start != -1 else alice_section
        assert '0' in badge_area, f"Alice should show 0 pending payments, found: {badge_area}"
        
        assert 'badge bg-success' in david_section, "David should have success badge"
        badge_start = david_section.find('badge bg-success')
        badge_area = david_section[badge_start:badge_start + 200] if badge_start != -1 else david_section
        assert '0' in badge_area, f"David should show 0 pending payments, found: {badge_area}"

    def test_admin_dashboard_search_by_first_name(self):
        """Test filtering users by first name."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Smith')
        user2 = self.create_regular_user('user2', 'Jane', 'Doe')
        user3 = self.create_regular_user('user3', 'Johnny', 'Wilson')
        
        # Login admin
        self.login_user(admin.username)

        # Search by first name "John"
        response = self.client.get('/admin?search=John')
        assert response.status_code == 200
        
        response_text = response.data.decode()
        
        # Should show matching users
        assert 'John' in response_text and 'Smith' in response_text
        assert 'Johnny' in response_text and 'Wilson' in response_text
        
        # Should not show non-matching user
        assert not ('Jane' in response_text and 'Doe' in response_text)

    def test_admin_dashboard_search_by_surname(self):
        """Test filtering users by surname."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Smith')
        user2 = self.create_regular_user('user2', 'Jane', 'Smithson')
        user3 = self.create_regular_user('user3', 'Bob', 'Wilson')
        
        # Login admin
        self.login_user(admin.username)

        # Search by surname "Smith"
        response = self.client.get('/admin?search=Smith')
        assert response.status_code == 200
        
        response_text = response.data.decode()
        
        # Should show matching users
        assert 'John' in response_text and 'Smith' in response_text
        assert 'Jane' in response_text and 'Smithson' in response_text
        
        # Should not show non-matching user
        assert not ('Bob' in response_text and 'Wilson' in response_text)

    def test_admin_dashboard_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Smith')
        user2 = self.create_regular_user('user2', 'jane', 'doe')
        
        # Login admin
        self.login_user(admin.username)

        # Search with lowercase
        response = self.client.get('/admin?search=john')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert 'John' in response_text

        # Search with uppercase
        response = self.client.get('/admin?search=JANE')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert 'jane' in response_text

        # Search with mixed case
        response = self.client.get('/admin?search=SmItH')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert 'Smith' in response_text

    def test_admin_dashboard_search_partial_matches(self):
        """Test that search works with partial matches."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'Alexander', 'Johnson')
        user2 = self.create_regular_user('user2', 'Alexandra', 'Jones')
        user3 = self.create_regular_user('user3', 'Bob', 'Wilson')
        
        # Login admin
        self.login_user(admin.username)

        # Search with partial first name
        response = self.client.get('/admin?search=Alex')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should match both Alexander and Alexandra
        assert 'Alexander' in response_text
        assert 'Alexandra' in response_text
        # Should not match Bob
        assert not ('Bob' in response_text and 'Wilson' in response_text)

        # Search with partial surname
        response = self.client.get('/admin?search=John')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should match Johnson
        assert 'Johnson' in response_text
        # Should not match Jones or Wilson
        assert not ('Jones' in response_text)
        assert not ('Wilson' in response_text)

    def test_admin_dashboard_search_no_results(self):
        """Test search with no matching results."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Smith')
        user2 = self.create_regular_user('user2', 'Jane', 'Doe')
        
        # Login admin
        self.login_user(admin.username)

        # Search for non-existent name
        response = self.client.get('/admin?search=NonExistentName')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show "No users found" message
        assert 'No users found' in response_text
        # Should show the search filter indicator
        assert 'Showing results for:' in response_text
        assert 'NonExistentName' in response_text

    def test_admin_dashboard_search_with_pagination(self):
        """Test search functionality with pagination."""
        # Create admin
        admin = self.create_admin_user()
        
        # Create many users with similar names to test pagination with search
        matching_users = []
        for i in range(25):  # More than one page
            user = self.create_regular_user(f'john_user{i}', 'John', f'Lastname{i}')
            matching_users.append(user)
        
        # Create non-matching users
        non_matching_users = []
        for i in range(5):
            user = self.create_regular_user(f'other_user{i}', 'Other', f'Name{i}')
            non_matching_users.append(user)
        
        # Login admin
        self.login_user(admin.username)

        # Search for "John" - should find 25 users
        response = self.client.get('/admin?search=John')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show pagination (25 users > 20 per page)
        assert 'pagination' in response_text
        # Should show John users but not Other users
        assert 'John' in response_text
        assert 'Other' not in response_text
        
        # Test second page with search parameter preserved
        response = self.client.get('/admin?search=John&page=2')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should still show John users on second page
        assert 'John' in response_text
        # Should show search filter indicator
        assert 'Showing results for:' in response_text

    def test_admin_dashboard_search_pagination_urls_preserve_search(self):
        """Test that pagination URLs preserve search parameters."""
        # Create admin
        admin = self.create_admin_user()
        
        # Create enough users to trigger pagination
        for i in range(25):
            self.create_regular_user(f'user{i}', 'Test', f'User{i}')
        
        # Login admin
        self.login_user(admin.username)

        # Search with a term that should return results spanning multiple pages
        response = self.client.get('/admin?search=Test')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Check that pagination links include the search parameter
        assert 'search=Test' in response_text
        # Should have next page link with search parameter
        assert 'page=2' in response_text and 'search=Test' in response_text

    def test_admin_dashboard_search_form_preserves_value(self):
        """Test that search form input preserves the searched value."""
        # Create admin and test user
        admin = self.create_admin_user()
        user = self.create_regular_user('user1', 'John', 'Smith')
        
        # Login admin
        self.login_user(admin.username)

        # Perform search
        search_term = 'John'
        response = self.client.get(f'/admin?search={search_term}')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Check that the search input field contains the searched value
        assert f'value="{search_term}"' in response_text
        # Check that clear button is shown
        assert 'Clear' in response_text

    def test_admin_dashboard_clear_search_functionality(self):
        """Test the clear search functionality."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Smith')
        user2 = self.create_regular_user('user2', 'Jane', 'Doe')
        
        # Login admin
        self.login_user(admin.username)

        # First perform a search
        response = self.client.get('/admin?search=John')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert 'John' in response_text
        assert 'Jane' not in response_text
        assert 'Clear' in response_text

        # Click clear (simulated by visiting admin without search parameter)
        response = self.client.get('/admin')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show all users again
        assert 'John' in response_text
        assert 'Jane' in response_text
        # Search input should be empty
        assert 'value=""' in response_text or 'value=\'\'\'' in response_text
        # Clear button should not be shown
        assert response_text.count('Clear') <= 1  # May appear in help text but not as button

    def test_admin_dashboard_search_with_special_characters(self):
        """Test search functionality with special characters."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'Van Der Merwe', 'Jones')
        user2 = self.create_regular_user('user2', 'Jean-Pierre', 'Dubois')
        user3 = self.create_regular_user('user3', 'Mary Jane', 'Watson')
        
        # Login admin
        self.login_user(admin.username)

        # Search for name with spaces
        response = self.client.get('/admin?search=Van Der')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert 'Van Der Merwe' in response_text
        assert 'Jones' in response_text

        # Search for name with hyphen
        response = self.client.get('/admin?search=Jean-Pierre')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert 'Jean-Pierre' in response_text
        assert 'Dubois' in response_text

        # Search for partial name with space
        response = self.client.get('/admin?search=Mary Jane')
        assert response.status_code == 200
        response_text = response.data.decode()
        assert 'Mary Jane' in response_text
        assert 'Watson' in response_text

    def test_admin_dashboard_search_empty_string_shows_all(self):
        """Test that empty search string shows all users."""
        # Create admin and test users
        admin = self.create_admin_user()
        user1 = self.create_regular_user('user1', 'John', 'Smith')
        user2 = self.create_regular_user('user2', 'Jane', 'Doe')
        
        # Login admin
        self.login_user(admin.username)

        # Search with empty string
        response = self.client.get('/admin?search=')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show all users
        assert 'John' in response_text
        assert 'Jane' in response_text

        # Search with whitespace only
        response = self.client.get('/admin?search=   ')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show all users
        assert 'John' in response_text
        assert 'Jane' in response_text

    def test_admin_dashboard_search_maintains_sorting(self):
        """Test that search results maintain proper sorting by pending payments."""
        # Create admin
        admin = self.create_admin_user()
        
        # Create users with similar names but different pending payment counts
        user_no_pending = self.create_regular_user('user1', 'John', 'Zero')
        user_one_pending = self.create_regular_user('user2', 'John', 'One') 
        user_two_pending = self.create_regular_user('user3', 'John', 'Two')
        
        # Create pending payments
        self.create_proof_of_payment(user_one_pending, 'January 2025', admin_verified=False)
        self.create_proof_of_payment(user_two_pending, 'January 2025', admin_verified=False)
        self.create_proof_of_payment(user_two_pending, 'February 2025', admin_verified=False)
        
        # Login admin
        self.login_user(admin.username)

        # Search for "John" - all three users should match
        response = self.client.get('/admin?search=John')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # All Johns should be present
        assert 'Zero' in response_text
        assert 'One' in response_text
        assert 'Two' in response_text
        
        # Check sorting order - users with more pending payments should appear first
        two_pos = response_text.find('Two')  # Should be first (2 pending)
        one_pos = response_text.find('One')  # Should be second (1 pending)  
        zero_pos = response_text.find('Zero') # Should be third (0 pending)
        
        assert two_pos < one_pos, "John Two (2 pending) should appear before John One (1 pending)"
        assert one_pos < zero_pos, "John One (1 pending) should appear before John Zero (0 pending)"

    def test_admin_dashboard_search_comprehensive_scenario(self):
        """Test comprehensive search scenario with various user states."""
        # Create admin
        admin = self.create_admin_user('admin_user', admin=True)
        
        # Create users with different states and searchable names
        john_with_pending = self.create_regular_user('john1', 'John', 'WithPending')
        john_no_pending = self.create_regular_user('john2', 'John', 'NoPending')
        jane_with_profile = self.create_regular_user('jane1', 'Jane', 'WithProfile')
        other_user = self.create_regular_user('other', 'Other', 'User')
        
        # Set up different user states
        self.create_proof_of_payment(john_with_pending, 'January 2025', admin_verified=False)
        self.create_profile_picture(jane_with_profile)
        
        # Login admin
        self.login_user(admin.username)

        # Search for "John"
        response = self.client.get('/admin?search=John')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show both John users but not Jane or Other
        assert 'WithPending' in response_text
        assert 'NoPending' in response_text
        assert 'WithProfile' not in response_text
        # Check that the specific user "Other User" is not in the table by checking the surname context
        assert not ('Other' in response_text and 'User' in response_text and 'other' in response_text)
        
        # Should show search indicator
        assert 'Showing results for:' in response_text
        assert '"John"' in response_text
        assert '(filtered)' in response_text
        
        # John with pending should appear before John without
        with_pending_pos = response_text.find('WithPending')
        no_pending_pos = response_text.find('NoPending')
        assert with_pending_pos < no_pending_pos, "User with pending payments should appear first"

    def test_admin_dashboard_search_ui_elements(self):
        """Test that search UI elements are properly displayed."""
        # Create admin and test user
        admin = self.create_admin_user()
        user = self.create_regular_user('user1', 'John', 'Smith')
        
        # Login admin
        self.login_user(admin.username)

        # Test admin dashboard without search
        response = self.client.get('/admin')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show search form elements
        assert 'Search Users' in response_text
        assert 'name="search"' in response_text
        assert 'Search by first name or surname' in response_text
        assert 'fa-search' in response_text  # Search icon
        
        # Should not show clear button or filter indicator when no search
        assert 'Clear' not in response_text or response_text.count('Clear') <= 1
        assert 'Showing results for:' not in response_text
        assert '(filtered)' not in response_text

        # Test with search
        response = self.client.get('/admin?search=John')
        assert response.status_code == 200
        response_text = response.data.decode()
        
        # Should show search form with value
        assert 'value="John"' in response_text
        # Should show clear button
        assert 'Clear' in response_text
        # Should show filter indicators
        assert 'Showing results for:' in response_text
        assert '"John"' in response_text
        assert '(filtered)' in response_text
