import os
import sys
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables first
load_dotenv()

# Import database and models
from database import engine, Base
from models.user import User
from models.conversation import Conversation, Message, ConversationParticipant

def init_db():
    """Initialize the database by creating all tables."""
    print("🔧 Initializing database...")
    try:
        # Drop all tables first (be careful with this in production!)
        print("Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Create all tables
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database initialized successfully!")
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = init_db()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
