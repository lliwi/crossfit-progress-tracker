#!/bin/bash
set -e

# Wait for database to be reachable (TCP check on db:5432)
echo "==> Waiting for database to be ready..."
python << 'PYEOF'
import socket, sys, time
for i in range(1, 31):
    try:
        s = socket.create_connection(("db", 5432), timeout=2)
        s.close()
        print("==> Database is ready.")
        sys.exit(0)
    except (socket.error, OSError):
        print(f"    Attempt {i}/30 - retrying in 2s...")
        time.sleep(2)
print("==> WARNING: Database not reachable after 60s, proceeding anyway...")
PYEOF

# Initialize migrations if not present
if [ ! -d "migrations" ]; then
    echo "==> Initializing Flask-Migrate..."
    flask db init
    flask db migrate -m "Initial migration"
fi

# Apply migrations
echo "==> Applying migrations..."
flask db upgrade

# Start gunicorn
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 wsgi:app
