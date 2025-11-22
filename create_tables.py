from app.database import engine, Base
# Import all models to ensure they are registered with Base
from app.models import User, Notebook, Document, Chat, Message, Citation, SummaryPack

if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
