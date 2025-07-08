aurora_motors/
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── gunicorn.conf.py
│
├── aurora_motors/                          # Main project directory
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py
│
├── apps/                                   # All Django apps
│   ├── __init__.py
│   │
│   ├── accounts/                          # User management
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── signals.py
│   │   ├── managers.py
│   │   ├── permissions.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── templates/
│   │       └── accounts/
│   │           ├── login.html
│   │           ├── register.html
│   │           ├── profile.html
│   │           └── dashboard.html
│   │
│   ├── vehicles/                          # Car management
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── filters.py
│   │   ├── managers.py
│   │   ├── choices.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── templates/
│   │       └── vehicles/
│   │           ├── vehicle_list.html
│   │           ├── vehicle_detail.html
│   │           ├── vehicle_search.html
│   │           └── vehicle_filter.html
│   │
│   ├── bookings/                          # Booking system
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── signals.py
│   │   ├── managers.py
│   │   ├── utils.py
│   │   ├── tasks.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── templates/
│   │       └── bookings/
│   │           ├── booking_form.html
│   │           ├── booking_confirmation.html
│   │           ├── booking_detail.html
│   │           ├── booking_list.html
│   │           └── calendar.html
│   │
│   ├── contracts/                         # Digital contracts
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── utils.py
│   │   ├── tasks.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── templates/
│   │       └── contracts/
│   │           ├── contract_signing.html
│   │           ├── contract_view.html
│   │           └── contract_list.html
│   │
│   ├── documents/                         # Document management
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── utils.py
│   │   ├── validators.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── templates/
│   │       └── documents/
│   │           ├── upload.html
│   │           ├── document_list.html
│   │           └── document_view.html
│   │
│   ├── notifications/                     # Email & notifications
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── tasks.py
│   │   ├── utils.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── templates/
│   │       └── notifications/
│   │           └── emails/
│   │               ├── booking_confirmation.html
│   │               ├── booking_reminder.html
│   │               └── contract_signed.html
│   │
│   ├── analytics/                         # Analytics & reports
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── utils.py
│   │   ├── charts.py
│   │   ├── migrations/
│   │   │   └── __init__.py
│   │   └── templates/
│   │       └── analytics/
│   │           ├── dashboard.html
│   │           ├── reports.html
│   │           └── charts.html
│   │
│   ├── core/                              # Core utilities
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── utils.py
│   │   ├── mixins.py
│   │   ├── decorators.py
│   │   ├── permissions.py
│   │   ├── pagination.py
│   │   ├── validators.py
│   │   └── middleware.py
│   │
│   └── api/                               # API endpoints
│       ├── __init__.py
│       ├── urls.py
│       ├── views.py
│       ├── serializers.py
│       ├── permissions.py
│       ├── throttling.py
│       └── v1/
│           ├── __init__.py
│           ├── urls.py
│           ├── views.py
│           └── serializers.py
│
├── static/                                # Static files
│   ├── css/
│   │   ├── base.css
│   │   ├── components.css
│   │   ├── dashboard.css
│   │   ├── booking.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── base.js
│   │   ├── booking.js
│   │   ├── calendar.js
│   │   ├── search.js
│   │   ├── contract-signing.js
│   │   └── admin.js
│   ├── images/
│   │   ├── logo.png
│   │   ├── favicon.ico
│   │   └── vehicles/
│   ├── fonts/
│   └── vendor/
│       ├── bootstrap/
│       ├── jquery/
│       └── fontawesome/
│
├── media/                                 # User uploaded files
│   ├── vehicles/
│   │   └── images/
│   ├── documents/
│   │   ├── licenses/
│   │   ├── contracts/
│   │   └── invoices/
│   └── users/
│       └── avatars/
│
├── templates/                             # Base templates
│   ├── base.html
│   ├── base_admin.html
│   ├── base_dashboard.html
│   ├── includes/
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   ├── footer.html
│   │   ├── messages.html
│   │   └── pagination.html
│   ├── errors/
│   │   ├── 404.html
│   │   ├── 500.html
│   │   └── 403.html
│   └── pages/
│       ├── home.html
│       ├── about.html
│       ├── contact.html
│       ├── privacy.html
│       └── terms.html
│
├── fixtures/                              # Sample data
│   ├── users.json
│   ├── vehicles.json
│   └── sample_data.json
│
├── locale/                                # Internationalization
│   ├── en/
│   │   └── LC_MESSAGES/
│   │       ├── django.po
│   │       └── django.mo
│   └── es/
│       └── LC_MESSAGES/
│           ├── django.po
│           └── django.mo
│
├── logs/                                  # Log files
│   ├── django.log
│   ├── error.log
│   └── access.log
│
├── tests/                                 # Test files
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_accounts/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   └── test_forms.py
│   ├── test_vehicles/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   └── test_filters.py
│   ├── test_bookings/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   └── test_utils.py
│   └── test_integration/
│       ├── __init__.py
│       └── test_booking_flow.py
│
├── scripts/                               # Utility scripts
│   ├── backup_db.py
│   ├── populate_sample_data.py
│   ├── cleanup_old_files.py
│   └── deploy.sh
│
├── docs/                                  # Documentation
│   ├── API.md
│   ├── DEPLOYMENT.md
│   ├── SETUP.md
│   └── USER_GUIDE.md
│
└── config/                                # Configuration files
    ├── celery/
    │   ├── celery.conf
    │   └── beat.conf
    ├── nginx/
    │   └── aurora_motors.conf
    └── supervisor/
        └── aurora_motors.conf



# Aurora Motors - Car Rental Management System

A comprehensive car rental management system built with Django, featuring vehicle management, booking system, digital contracts, document management, and analytics.

## Features

- **User Management**: Customer registration, profiles, and staff management
- **Vehicle Management**: Fleet management with categories, brands, and features
- **Booking System**: Real-time availability checking and calendar-based booking
- **Digital Contracts**: Electronic signature system with templates
- **Document Management**: Upload, review, and compliance tracking
- **Notification System**: Multi-channel notifications (Email, SMS, Push, In-app)
- **Analytics & Reporting**: Business intelligence and custom reports
- **REST API**: Complete API for mobile and third-party integrations

## Technology Stack

- **Backend**: Django 4.2 with PostgreSQL
- **Frontend**: Bootstrap 5 with custom CSS/JavaScript
- **Task Queue**: Celery with Redis
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx + Gunicorn

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd aurora_motors



python manage.py makemigrations accounts
python manage.py migrate

python manage.py makemigrations accounts vehicles bookings contracts documents notifications analytics core


python manage.py makemigrations accounts
python manage.py makemigrations vehicles
python manage.py makemigrations bookings
python manage.py makemigrations contracts
python manage.py makemigrations documents
python manage.py makemigrations notifications
python manage.py makemigrations analytics
python manage.py makemigrations core

python manage.py collectstatic

python manage.py runserver
