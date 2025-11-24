import pytest
from datetime import date, datetime, timedelta
from app import create_app, db
from app.models import User, TrainingAttendance


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


class TestTrainingAttendance:
    
    def test_add_training_session_success(self, client, auth_user):
        """Test successfully adding a training session"""
        today = date.today()
        
        response = client.post('/profile/training/add', data={
            'training_date': today.strftime('%Y-%m-%d'),
            'hours': '2.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry added successfully' in response.data
        
        # Verify data was saved to database
        training = TrainingAttendance.query.filter_by(user_id=auth_user.id).first()
        assert training is not None
        assert training.training_date == today
        assert training.hours == 2.0

    def test_add_training_session_with_decimal_hours(self, client, auth_user):
        """Test adding a training session with decimal hours"""
        today = date.today()
        
        response = client.post('/profile/training/add', data={
            'training_date': today.strftime('%Y-%m-%d'),
            'hours': '1.5'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry added successfully' in response.data
        
        # Verify data was saved to database
        training = TrainingAttendance.query.filter_by(user_id=auth_user.id).first()
        assert training is not None
        assert training.hours == 1.5

    def test_add_training_session_duplicate_date(self, client, auth_user):
        """Test that duplicate training sessions for the same date are rejected"""
        today = date.today()
        
        # Add first session
        client.post('/profile/training/add', data={
            'training_date': today.strftime('%Y-%m-%d'),
            'hours': '2.0'
        })
        
        # Try to add second session for same date
        response = client.post('/profile/training/add', data={
            'training_date': today.strftime('%Y-%m-%d'),
            'hours': '1.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry already exists for this date' in response.data
        
        # Verify only one entry exists
        training_count = TrainingAttendance.query.filter_by(user_id=auth_user.id).count()
        assert training_count == 1

    def test_add_training_session_invalid_hours(self, client, auth_user):
        """Test validation for invalid hours"""
        today = date.today()
        
        # Test negative hours
        response = client.post('/profile/training/add', data={
            'training_date': today.strftime('%Y-%m-%d'),
            'hours': '-1.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training hours must be greater than 0' in response.data
        
        # Test excessive hours
        response = client.post('/profile/training/add', data={
            'training_date': today.strftime('%Y-%m-%d'),
            'hours': '25.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training hours cannot exceed 24 hours' in response.data
        
        # Verify no entries were created
        training_count = TrainingAttendance.query.filter_by(user_id=auth_user.id).count()
        assert training_count == 0

    def test_add_training_session_missing_fields(self, client, auth_user):
        """Test validation when required fields are missing"""
        # Missing date
        response = client.post('/profile/training/add', data={
            'hours': '2.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training date and hours are required' in response.data
        
        # Missing hours
        response = client.post('/profile/training/add', data={
            'training_date': date.today().strftime('%Y-%m-%d')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training date and hours are required' in response.data

    def test_edit_training_session_success(self, client, auth_user):
        """Test successfully editing a training session"""
        # Create a training session first
        yesterday = date.today() - timedelta(days=1)
        training = TrainingAttendance(
            user_id=auth_user.id,
            training_date=yesterday,
            hours=2.0
        )
        db.session.add(training)
        db.session.commit()
        
        # Edit the session
        response = client.post(f'/profile/training/edit/{training.id}', data={
            'training_date': yesterday.strftime('%Y-%m-%d'),
            'hours': '3.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry updated successfully' in response.data
        
        # Verify changes were saved
        updated_training = TrainingAttendance.query.get(training.id)
        assert updated_training.hours == 3.0

    def test_edit_training_session_change_date(self, client, auth_user):
        """Test editing a training session by changing the date"""
        # Create a training session
        yesterday = date.today() - timedelta(days=1)
        two_days_ago = date.today() - timedelta(days=2)
        
        training = TrainingAttendance(
            user_id=auth_user.id,
            training_date=yesterday,
            hours=2.0
        )
        db.session.add(training)
        db.session.commit()
        
        # Edit to change date
        response = client.post(f'/profile/training/edit/{training.id}', data={
            'training_date': two_days_ago.strftime('%Y-%m-%d'),
            'hours': '2.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry updated successfully' in response.data
        
        # Verify date was changed
        updated_training = TrainingAttendance.query.get(training.id)
        assert updated_training.training_date == two_days_ago

    def test_edit_training_session_date_conflict(self, client, auth_user):
        """Test editing a training session to a date that already has an entry"""
        yesterday = date.today() - timedelta(days=1)
        two_days_ago = date.today() - timedelta(days=2)
        
        # Create two training sessions
        training1 = TrainingAttendance(
            user_id=auth_user.id,
            training_date=yesterday,
            hours=2.0
        )
        training2 = TrainingAttendance(
            user_id=auth_user.id,
            training_date=two_days_ago,
            hours=1.5
        )
        db.session.add_all([training1, training2])
        db.session.commit()
        
        # Try to edit training2 to yesterday's date (conflict with training1)
        response = client.post(f'/profile/training/edit/{training2.id}', data={
            'training_date': yesterday.strftime('%Y-%m-%d'),
            'hours': '3.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry already exists for this date' in response.data
        
        # Verify original data remains unchanged
        unchanged_training = TrainingAttendance.query.get(training2.id)
        assert unchanged_training.training_date == two_days_ago
        assert unchanged_training.hours == 1.5

    def test_edit_nonexistent_training_session(self, client, auth_user):
        """Test editing a training session that doesn't exist"""
        response = client.post('/profile/training/edit/999', data={
            'training_date': date.today().strftime('%Y-%m-%d'),
            'hours': '2.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry not found' in response.data

    def test_edit_other_users_training_session(self, client, auth_user):
        """Test that users cannot edit other users' training sessions"""
        # Create another user
        other_user = User(
            first_name='Other',
            surname='User',
            username='otheruser'
        )
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()
        
        # Create training session for other user
        training = TrainingAttendance(
            user_id=other_user.id,
            training_date=date.today(),
            hours=2.0
        )
        db.session.add(training)
        db.session.commit()
        
        # Try to edit other user's session
        response = client.post(f'/profile/training/edit/{training.id}', data={
            'training_date': date.today().strftime('%Y-%m-%d'),
            'hours': '3.0'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry not found' in response.data
        
        # Verify other user's data wasn't changed
        unchanged_training = TrainingAttendance.query.get(training.id)
        assert unchanged_training.hours == 2.0

    def test_delete_training_session_success(self, client, auth_user):
        """Test successfully deleting a training session"""
        # Create a training session
        yesterday = date.today() - timedelta(days=1)
        training = TrainingAttendance(
            user_id=auth_user.id,
            training_date=yesterday,
            hours=2.0
        )
        db.session.add(training)
        db.session.commit()
        training_id = training.id
        
        # Delete the session
        response = client.post(f'/profile/training/delete/{training_id}', 
                             follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry deleted successfully' in response.data
        
        # Verify it was deleted from database
        deleted_training = TrainingAttendance.query.get(training_id)
        assert deleted_training is None

    def test_delete_nonexistent_training_session(self, client, auth_user):
        """Test deleting a training session that doesn't exist"""
        response = client.post('/profile/training/delete/999', 
                             follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry not found' in response.data

    def test_delete_other_users_training_session(self, client, auth_user):
        """Test that users cannot delete other users' training sessions"""
        # Create another user
        other_user = User(
            first_name='Other',
            surname='User',
            username='otheruser'
        )
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()
        
        # Create training session for other user
        training = TrainingAttendance(
            user_id=other_user.id,
            training_date=date.today(),
            hours=2.0
        )
        db.session.add(training)
        db.session.commit()
        
        # Try to delete other user's session
        response = client.post(f'/profile/training/delete/{training.id}', 
                             follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Training entry not found' in response.data
        
        # Verify other user's data still exists
        existing_training = TrainingAttendance.query.get(training.id)
        assert existing_training is not None

    def test_profile_displays_training_data_grouped_by_month(self, client, auth_user):
        """Test that profile page displays training data grouped by month/year"""
        # Create training sessions across different months
        nov_2025 = date(2025, 11, 15)
        oct_2025 = date(2025, 10, 20)
        sep_2025 = date(2025, 9, 10)
        
        training_sessions = [
            TrainingAttendance(user_id=auth_user.id, training_date=nov_2025, hours=2.5),
            TrainingAttendance(user_id=auth_user.id, training_date=oct_2025, hours=1.5),
            TrainingAttendance(user_id=auth_user.id, training_date=sep_2025, hours=3.0),
        ]
        
        db.session.add_all(training_sessions)
        db.session.commit()
        
        # Check profile page
        response = client.get('/profile')
        assert response.status_code == 200
        
        # Verify monthly grouping and totals are displayed
        assert b'November 2025' in response.data
        assert b'October 2025' in response.data
        assert b'September 2025' in response.data
        assert b'2.5 hours total' in response.data
        assert b'1.5 hours total' in response.data
        assert b'3.0 hours total' in response.data

    def test_profile_displays_individual_training_sessions(self, client, auth_user):
        """Test that profile page displays individual training sessions with dates and hours"""
        yesterday = date.today() - timedelta(days=1)
        training = TrainingAttendance(
            user_id=auth_user.id,
            training_date=yesterday,
            hours=2.5
        )
        db.session.add(training)
        db.session.commit()
        
        response = client.get('/profile')
        assert response.status_code == 200
        
        # Check that the training session is displayed
        formatted_date = yesterday.strftime('%B %d, %Y')
        assert formatted_date.encode() in response.data
        assert b'2.5 hours' in response.data

    def test_profile_displays_no_training_message_when_empty(self, client, auth_user):
        """Test that profile page shows appropriate message when no training sessions exist"""
        response = client.get('/profile')
        assert response.status_code == 200
        assert b'No training sessions recorded yet' in response.data
        assert b'Add your first training session above' in response.data

    def test_training_sessions_sorted_by_date_descending(self, client, auth_user):
        """Test that training sessions are sorted with most recent first"""
        # Create sessions in different order than we want them displayed
        dates_and_hours = [
            (date(2025, 9, 1), 1.0),
            (date(2025, 11, 1), 2.0),
            (date(2025, 10, 1), 3.0),
        ]
        
        for training_date, hours in dates_and_hours:
            training = TrainingAttendance(
                user_id=auth_user.id,
                training_date=training_date,
                hours=hours
            )
            db.session.add(training)
        
        db.session.commit()
        
        response = client.get('/profile')
        content = response.data.decode()
        
        # Find positions of the months in the response
        nov_pos = content.find('November 2025')
        oct_pos = content.find('October 2025')
        sep_pos = content.find('September 2025')
        
        # November should come first (most recent), then October, then September
        assert nov_pos != -1 and oct_pos != -1 and sep_pos != -1
        assert nov_pos < oct_pos < sep_pos

    def test_monthly_totals_calculation(self, client, auth_user):
        """Test that monthly totals are calculated correctly"""
        # Create multiple sessions in the same month
        nov_date1 = date(2025, 11, 1)
        nov_date2 = date(2025, 11, 15)
        nov_date3 = date(2025, 11, 30)
        
        training_sessions = [
            TrainingAttendance(user_id=auth_user.id, training_date=nov_date1, hours=1.5),
            TrainingAttendance(user_id=auth_user.id, training_date=nov_date2, hours=2.0),
            TrainingAttendance(user_id=auth_user.id, training_date=nov_date3, hours=0.5),
        ]
        
        db.session.add_all(training_sessions)
        db.session.commit()
        
        response = client.get('/profile')
        assert response.status_code == 200
        
        # Total should be 1.5 + 2.0 + 0.5 = 4.0 hours
        assert b'4.0 hours total' in response.data
