import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    print("Testing password hashing...")
    from app.services.auth_service import get_password_hash
    hash = get_password_hash("testpassword")
    print(f"Hashing successful: {hash[:10]}...")
except Exception as e:
    print(f"Hashing failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nTesting database connection...")
    from app.database import SessionLocal
    db = SessionLocal()
    print("Database session created.")
    from app.models import User
    user = db.query(User).first()
    print(f"Database query successful. Found user: {user}")
    db.close()
except Exception as e:
    print(f"Database failed: {e}")
    import traceback
    traceback.print_exc()
