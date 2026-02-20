#!/bin/sh
set -e

# Run database migrations (or create tables if missing)
echo "Initializing database..."
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
echo "Creating admin user..."
python -m app.scripts.create_admin

# If arguments provided, exec them (e.g., gateway, worker)
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# Start the gRPC server as default command
echo "Starting gRPC server..."
exec python -m app.main
