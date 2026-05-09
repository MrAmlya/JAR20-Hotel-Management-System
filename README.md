# JAR20 Hotel Management System

A Django-based hotel management system for managing staff, customers, rooms,
reservations, check-ins, and check-outs.

## Features

- Staff signup and authentication
- Room, room type, and facility management
- Customer and reservation management
- Guest list for active stays
- Check-in and check-out workflow
- Payment summary calculations

## Local Setup

Create and activate a fresh virtual environment:

```shell
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```shell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Apply database migrations:

```shell
python manage.py migrate
```

Create an admin user:

```shell
python manage.py createsuperuser
```

Run the development server:

```shell
python manage.py runserver
```

Open the app at:

```text
http://127.0.0.1:8000/
```

## Configuration

The project works locally with default settings. For deployment or demos, these
environment variables can be set:

```shell
export SECRET_KEY="use-a-long-random-secret-key-for-production"
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,your-domain.com"
```

When `DJANGO_DEBUG=False`, the app enables secure browser headers, secure
cookies, HTTPS redirects, and HSTS by default. If your hosting provider handles
HTTPS redirects separately, you can override the redirect setting:

```shell
export DJANGO_SECURE_SSL_REDIRECT=False
```

## Notes

- The project uses SQLite by default.
- The old committed `myvenv` directory is ignored going forward. Use `.venv`
  for local development.
- This project currently targets Django 2.2 LTS.
