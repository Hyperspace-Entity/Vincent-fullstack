"""Production-safe entry point - never use debug mode in production."""

import os
import sys

from app import create_app

if __name__ == "__main__":
    # Determine config
    flask_env = os.environ.get("FLASK_ENV", "development")
    
    # Strict validation for production
    if flask_env == "production":
        required_keys = ["SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL"]
        missing_keys = [key for key in required_keys if not os.environ.get(key)]
        if missing_keys:
            print(f"ERROR: Missing required environment variables: {', '.join(missing_keys)}")
            sys.exit(1)
        
        # Verify key lengths
        if len(os.environ.get("SECRET_KEY", "")) < 32:
            print("ERROR: SECRET_KEY must be at least 32 characters")
            sys.exit(1)
    
    app = create_app(flask_env)
    
    # Development: use Flask dev server
    if flask_env == "development":
        print("\n" + "="*60)
        print("DEVELOPMENT SERVER - DEBUG MODE ENABLED")
        print("Never use this in production!")
        print("="*60 + "\n")
        app.run(debug=True, host="127.0.0.1", port=5000)
    
    # Production: use Gunicorn (external WSGI server)
    else:
        print("\nProduction mode: Use Gunicorn or similar WSGI server")
        print("Example: gunicorn -w 4 -b 0.0.0.0:8000 run:app")
        print("\nTo run with this script in production, set FLASK_ENV=development")
        print("and run through a production WSGI server like Gunicorn.\n")
        sys.exit(0)
