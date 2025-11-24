import pytest
import base64
from datetime import datetime, date
from app import create_app
from app.models import db


def create_test_user(app):
    """Helper function to create a test user and return user_id"""
    with app.app_context():
        from app.models import User
        user = User(first_name='Test', surname='User', username='testuser')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture(scope='session')
def app():
    """Create and configure a test app instance."""
    app = create_app('development')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='session')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='session')
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing"""
    with app.app_context():
        from app.models import User
        user = User(
            first_name='Admin',
            surname='User',
            username='admin',
            admin=True
        )
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def regular_user(app):
    """Create a regular user for testing"""
    with app.app_context():
        from app.models import User
        user = User(
            first_name='Regular',
            surname='User',
            username='regular'
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def another_user(app):
    """Create another user for testing"""
    with app.app_context():
        from app.models import User
        user = User(
            first_name='Another',
            surname='User',
            username='another'
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def another_admin_user(app):
    """Create another admin user for testing"""
    with app.app_context():
        from app.models import User
        user = User(
            first_name='Another',
            surname='Admin',
            username='admin2',
            admin=True
        )
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def regular_user_with_data(app):
    """Create a regular user with aikido info and training data"""
    with app.app_context():
        from app.models import User, AikidoInformation, TrainingAttendance
        
        # Create user
        user = User(
            first_name='Data',
            surname='User',
            username='datauser'
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.flush()
        
        # Create aikido info
        aikido_info = AikidoInformation(
            user_id=user.id,
            aikido_type='Aikikai',
            aikido_rank='1st Dan',
            certificate_no='TEST123',
            afsa_no='AFSA123',
            aif_no='AIF123',
            honbu_no='HONBU123'
        )
        db.session.add(aikido_info)
        
        # Create training session
        training_session = TrainingAttendance(
            user_id=user.id,
            training_date=date.today(),
            hours=2.0
        )
        db.session.add(training_session)
        
        db.session.commit()
        yield user, aikido_info, training_session
        
        # Cleanup
        db.session.delete(training_session)
        db.session.delete(aikido_info)
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def regular_user_with_proof_of_payment(app):
    """Create a regular user with an unverified proof of payment"""
    with app.app_context():
        from app.models import User, Attachment, ProofOfPayment
        
        # Create user
        user = User(
            first_name='Payment',
            surname='User',
            username='paymentuser'
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.flush()
        
        # Create fake image data
        fake_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
        encoded_data = base64.b64encode(fake_image_data).decode('utf-8')
        
        # Create attachment
        attachment = Attachment(
            user_id=user.id,
            type='pop',
            filename='test_payment.png',
            data=encoded_data
        )
        db.session.add(attachment)
        db.session.flush()
        
        # Create proof of payment
        pop = ProofOfPayment(
            user_id=user.id,
            attachment_id=attachment.id,
            month_year='January 2025',
            admin_verified=False
        )
        db.session.add(pop)
        
        db.session.commit()
        yield user, pop, attachment
        
        # Cleanup
        db.session.delete(pop)
        db.session.delete(attachment)
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def regular_user_with_verified_proof_of_payment(app):
    """Create a regular user with a verified proof of payment"""
    with app.app_context():
        from app.models import User, Attachment, ProofOfPayment
        
        # Create user
        user = User(
            first_name='Verified',
            surname='User',
            username='verifieduser'
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.flush()
        
        # Create fake image data
        fake_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
        encoded_data = base64.b64encode(fake_image_data).decode('utf-8')
        
        # Create attachment
        attachment = Attachment(
            user_id=user.id,
            type='pop',
            filename='verified_payment.png',
            data=encoded_data
        )
        db.session.add(attachment)
        db.session.flush()
        
        # Create verified proof of payment
        pop = ProofOfPayment(
            user_id=user.id,
            attachment_id=attachment.id,
            month_year='December 2024',
            admin_verified=True
        )
        db.session.add(pop)
        
        db.session.commit()
        yield user, pop, attachment
        
        # Cleanup
        db.session.delete(pop)
        db.session.delete(attachment)
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def regular_user_with_certificate(app):
    """Create a regular user with an aikido certificate"""
    with app.app_context():
        from app.models import User, Attachment
        
        # Create user
        user = User(
            first_name='Certificate',
            surname='User',
            username='certuser'
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.flush()
        
        # Create fake PDF data
        fake_pdf_data = b'%PDF-1.4 fake pdf data'
        encoded_data = base64.b64encode(fake_pdf_data).decode('utf-8')
        
        # Create certificate attachment
        certificate = Attachment(
            user_id=user.id,
            type='aikido_certificate',
            filename='test_certificate.pdf',
            data=encoded_data
        )
        db.session.add(certificate)
        
        db.session.commit()
        yield user, certificate
        
        # Cleanup
        db.session.delete(certificate)
        db.session.delete(user)
        db.session.commit()
