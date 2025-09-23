# Municipal Wallet System

A secure multi-signature wallet system for municipal financial management built with Django and Tailwind CSS.

## Features

### Core Functionality
- **Multi-Signature Approvals**: Deposits require 3 approvals, withdrawals require 5 approvals
- **Role-Based Access Control**: Different user roles with specific permissions
- **Transaction Management**: Create, track, and manage financial transactions
- **Real-time Notifications**: Email and SMS notifications for approvals
- **Audit Trail**: Complete logging of all system activities
- **Responsive UI**: Modern interface built with Tailwind CSS

### User Roles
- **Administrator**: Full system access
- **Mayor**: Can create transactions and approve
- **Treasurer**: Can create transactions and approve
- **Council Member**: Can approve transactions
- **Auditor**: Can view audit logs and reports
- **Viewer**: Read-only access

## Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Frontend**: HTML, Tailwind CSS, Alpine.js
- **Database**: PostgreSQL (configurable)
- **Authentication**: Django's built-in auth with custom user model
- **Notifications**: Email (SMTP) and SMS (Twilio)
- **Task Queue**: Celery with Redis
- **Deployment**: Docker-ready

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Redis (for Celery)
- Node.js (for frontend assets)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd municipal-wallet
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Load sample data (optional)**
   ```bash
   python manage.py loaddata fixtures/sample_data.json
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Run Celery worker (in separate terminal)**
   ```bash
   celery -A municipal_wallet worker -l info
   ```

9. **Run Celery beat (in separate terminal)**
   ```bash
   celery -A municipal_wallet beat -l info
   ```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/municipal_wallet

# Security
SECRET_KEY=your-secret-key-here
DEBUG=True

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@municipalwallet.com

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Approval Settings
DEPOSIT_APPROVALS_REQUIRED=3
WITHDRAWAL_APPROVALS_REQUIRED=5
APPROVAL_TIMEOUT_HOURS=72
```

## Usage

### Creating a Transaction

1. **Login** to the system with appropriate credentials
2. **Navigate** to the "Create Transaction" page
3. **Select** transaction type (Deposit or Withdrawal)
4. **Choose** the target account
5. **Enter** amount and description
6. **Submit** the transaction

### Approving Transactions

1. **Login** as an approver
2. **Navigate** to "Pending Approvals"
3. **Review** transaction details
4. **Approve** or **Reject** with optional comments
5. **System** automatically processes when all approvals are received

### Managing Users

1. **Login** as Administrator
2. **Navigate** to Admin panel
3. **Create** new users with appropriate roles
4. **Assign** users to cities
5. **Manage** user permissions

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/update/` - Update user profile

### Transactions
- `GET /api/transactions/` - List transactions
- `POST /api/transactions/` - Create transaction
- `GET /api/transactions/{id}/` - Get transaction details
- `PUT /api/transactions/{id}/` - Update transaction
- `DELETE /api/transactions/{id}/` - Delete transaction
- `POST /api/transactions/{id}/cancel/` - Cancel transaction

### Approvals
- `GET /api/approvals/pending/` - Get pending approvals
- `PUT /api/approvals/deposit/{id}/` - Approve/reject deposit
- `PUT /api/approvals/withdrawal/{id}/` - Approve/reject withdrawal

### Notifications
- `GET /api/notifications/` - List notifications
- `PUT /api/notifications/{id}/mark-read/` - Mark as read
- `GET /api/notifications/unread-count/` - Get unread count

## Security Features

- **Multi-Factor Authentication**: Optional 2FA support
- **Rate Limiting**: API rate limiting to prevent abuse
- **Audit Logging**: Complete audit trail of all actions
- **Role-Based Access**: Granular permissions system
- **Data Encryption**: Sensitive data encryption at rest
- **CSRF Protection**: Cross-site request forgery protection
- **XSS Protection**: Cross-site scripting protection

## Deployment

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t municipal-wallet .
   ```

2. **Run with docker-compose**
   ```bash
   docker-compose up -d
   ```

### Production Deployment

1. **Set up production database**
2. **Configure environment variables**
3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

5. **Set up web server** (Nginx + Gunicorn)
6. **Configure SSL certificates**
7. **Set up monitoring and logging**

## Monitoring and Maintenance

### Health Checks
- Database connectivity
- Redis connectivity
- Celery worker status
- Email service status

### Logging
- Application logs in `logs/django.log`
- Error tracking and monitoring
- Performance metrics

### Backup Strategy
- Database backups
- File system backups
- Configuration backups

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Changelog

### Version 1.0.0
- Initial release
- Multi-signature approval system
- Role-based access control
- Transaction management
- Notification system
- Audit logging
- Responsive UI with Tailwind CSS
