#!/bin/bash
set -e

# Initialize migrations if not present
if [ ! -d "migrations" ]; then
    echo "Initializing Flask-Migrate..."
    flask db init
    flask db migrate -m "Initial migration"
fi

# Apply migrations
flask db upgrade

# Start gunicorn
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 wsgi:app
