from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.http import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
from sqlalchemy.ext.declarative import declarative_base

# Base class for all models
Base = declarative_base()

__all__ = ['Base']



# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Travel App API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_tags=[

    ],
)

# Security scheme for Swagger UI
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Custom token scheme
class TokenBearer(HTTPBearer):
    async def __call__(self, request: Request) -> str:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Not authenticated"
            )
        return credentials.credentials

oauth2_scheme = TokenBearer()

# Database models 
class UserBase(BaseModel):
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True

class UserInDB(UserBase):
    id: int
    hashed_password: str

class MessageBase(BaseModel):
    content: str
    sender_id: int
    receiver_id: int

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    timestamp: datetime
    is_read: bool = False

    class Config:
        from_attributes = True

class Chat(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    last_message: Optional[Message] = None
    unread_count: int = 0

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mock databases
users_db = {}
chats_db = {}
messages_db = {}



# WebSocket connections
active_connections: Dict[int, WebSocket] = {}

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Add a test user if the database is empty
if not users_db:
    test_user = {
        "id": 1,  # First user gets ID 1
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "hashed_password": get_password_hash("testpassword"),
        "is_active": True
    }
    users_db[test_user["username"]] = test_user
    print(f"Initialized test user with ID {test_user['id']}: {test_user}")


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(auth_db, username: str, password: str):
    user = get_user(auth_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Find the user in the  database
        user = next((u for u in users_db.values() if u["username"] == username), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        return UserInDB(
            id=user["id"],
            username=username,
            email=user.get("email", ""),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            hashed_password=user["hashed_password"],
            is_active=user.get("is_active", True)
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth routes
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/logon", tags=["authentication"])
async def login_for_access_token(login_data: LoginRequest):
    
    user = None
    for username, user_data in users_db.items():
        if user_data.get('email') == login_data.email:
            user = get_user(users_db, username)
            break
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"token": access_token}

@app.post("/api/auth/register", response_model=User, tags=["authentication"])
async def register_user(user: UserCreate):
    # Check if username or email already exists
    if any(u["username"] == user.username for u in users_db.values()):
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    if any(u["email"] == user.email for u in users_db.values()):
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user with incremented ID
    user_id = max([u["id"] for u in users_db.values()], default=0) + 1
    new_user = {
        "id": user_id,  # This will be 1 for first user, 2 for second, etc.
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "hashed_password": get_password_hash(user.password),
        "is_active": True
    }
    
    # Add to database
    users_db[user.username] = new_user
    print(f"New user registered: {new_user}")
    
    # Return user data without password
    return User(
        id=new_user['id'],
        username=new_user['username'],
        email=new_user['email'],
        first_name=new_user.get('first_name'),
        last_name=new_user.get('last_name'),
        is_active=new_user.get('is_active', True)
    )

# User routes
# @app.get(
#     "/api/users/me/", 
#     response_model=User,
#     dependencies=[Depends(security)],
#     tags=["users"]
# )
# async def read_users_me(current_user: User = Depends(get_current_user)):

#     return current_user

@app.get(
    "/api/users/",
    response_model=List[User],
    dependencies=[Depends(security)],
    tags=["users"]
)
async def get_all_users(current_user: User = Depends(get_current_user)):

    users = []
    for user_data in users_db.values():
        user_dict = user_data.copy()
        user_dict.pop('hashed_password', None)  # Remove password hash
        users.append(User(**user_dict))
    
    print(f"Returning {len(users)} users")
    return users

@app.get(
    "/api/users/{user_id}",
    response_model=User,
    dependencies=[Depends(security)],
    tags=["users"]
)
async def get_user_by_id(user_id: int, current_user: User = Depends(get_current_user)):
   
    user = next((u for u in users_db.values() if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return User(**user)

class UserUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None

@app.put(
    "/api/users/{user_id}",
    response_model=User,
    dependencies=[Depends(security)],
    tags=["users"]
)
async def update_user(
    user_id: int, 
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    
    user = next((u for u in users_db.values() if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user data
    if user_update.email is not None:
        user["email"] = user_update.email
    if user_update.first_name is not None:
        user["first_name"] = user_update.first_name
    if user_update.last_name is not None:
        user["last_name"] = user_update.last_name
    if user_update.password is not None:
        user["hashed_password"] = get_password_hash(user_update.password)
    
    return User(**user)

@app.delete(
    "/api/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(security)],
    tags=["users"]
)
async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):

    user_key = next((k for k, v in users_db.items() if v["id"] == user_id), None)
    if not user_key:
        raise HTTPException(status_code=404, detail="User not found")

    del users_db[user_key]
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Chat WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            await handle_websocket_message(user_id, message_data)
    except WebSocketDisconnect:
        active_connections.pop(user_id, None)

async def handle_websocket_message(sender_id: int, data: dict):
    message_type = data.get('type')
    
    if message_type == 'message':
        receiver_id = data.get('receiver_id')
        content = data.get('content')
        
        # Create new message
        message_id = max(messages_db.keys(), default=0) + 1
        message = {
            'id': message_id,
            'content': content,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'timestamp': datetime.utcnow(),
            'is_read': False
        }
        messages_db[message_id] = message
        
        # Update chat
        chat_id = get_or_create_chat(sender_id, receiver_id)
        chats_db[chat_id]['last_message'] = message
        chats_db[chat_id]['unread_count'] += 1
        
        # Notify receiver if online
        if receiver_id in active_connections:
            await active_connections[receiver_id].send_json({
                'type': 'new_message',
                'chat_id': chat_id,
                'message': message
            })

# Helper function to get or create a chat between two users
def get_or_create_chat(user1_id: int, user2_id: int) -> int:
    # Create a unique chat ID based on user IDs
    chat_id = hash(frozenset({user1_id, user2_id}))
    
    if chat_id not in chats_db:
        chats_db[chat_id] = {
            'id': chat_id,
            'user1_id': min(user1_id, user2_id),
            'user2_id': max(user1_id, user2_id),
            'last_message': None,
            'unread_count': 0
        }
    
    return chat_id

# Chat REST endpoints


class CreateChatRequest(BaseModel):
    user_id: int

@app.post("/api/chats/create/", response_model=Dict[str, Any], tags =["Chat functionality"])
async def create_chat(
    chat_request: CreateChatRequest,
    current_user: User = Depends(get_current_user)
):

    other_user_id = chat_request.user_id
    
    # Check if other user exists
    other_user = next((u for u in users_db.values() if u['id'] == other_user_id), None)
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create or get existing chat
    chat_id = get_or_create_chat(current_user.id, other_user_id)
    chat = chats_db[chat_id]
    
    return {
        'id': chat_id,
        'user1_id': chat['user1_id'],
        'user2_id': chat['user2_id'],
        'other_user': {
            'id': other_user['id'],
            'username': other_user['username'],
            'first_name': other_user.get('first_name'),
            'last_name': other_user.get('last_name')
        },
        'last_message': None,
        'unread_count': 0
    }
@app.get("/api/chats/", response_model=List[Dict[str, Any]],
         tags =["Chat functionality"]
         )
async def get_user_chats(current_user: User = Depends(get_current_user)):
    user_chats = []
    for chat in chats_db.values():
        if chat['user1_id'] == current_user.id or chat['user2_id'] == current_user.id:
            # Get other user's info
            other_user_id = chat['user2_id'] if chat['user1_id'] == current_user.id else chat['user1_id']
            other_user = next((u for u in users_db.values() if u['id'] == other_user_id), None)
            
            if other_user:
                user_chats.append({
                    'id': chat['id'],
                    'other_user': {
                        'id': other_user['id'],
                        'username': other_user['username'],
                        'first_name': other_user.get('first_name'),
                        'last_name': other_user.get('last_name')
                    },
                    'last_message': chat['last_message'],
                    'unread_count': chat['unread_count']
                })
    
    return user_chats

@app.get("/api/chats/{other_user_id}/messages", response_model=List[Dict[str, Any]],
         tags =["Chat functionality"]
         )
async def get_chat_messages(
    other_user_id: int,
    current_user: User = Depends(get_current_user)
):
    # Find or create chat
    chat_id = get_or_create_chat(current_user.id, other_user_id)
    
    # Get messages between these users
    messages = [
        msg for msg in messages_db.values()
        if (msg['sender_id'] == current_user.id and msg['receiver_id'] == other_user_id) or
           (msg['sender_id'] == other_user_id and msg['receiver_id'] == current_user.id)
    ]
    
    # Mark messages as read
    for msg in messages:
        if msg['receiver_id'] == current_user.id and not msg['is_read']:
            msg['is_read'] = True
            messages_db[msg['id']]['is_read'] = True
            chats_db[chat_id]['unread_count'] = max(0, chats_db[chat_id]['unread_count'] - 1)
    
    return sorted(messages, key=lambda x: x['timestamp'])

@app.post("/api/chats/{receiver_id}/messages", response_model=Dict[str, Any],
          tags =["Chat functionality"]
          )
async def send_message(
    receiver_id: int,
    message: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    # Check if receiver exists
    if not any(u['id'] == receiver_id for u in users_db.values()):
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    # Create message
    message_id = max(messages_db.keys(), default=0) + 1
    new_message = {
        'id': message_id,
        'content': message.get('content', ''),
        'sender_id': current_user.id,
        'receiver_id': receiver_id,
        'timestamp': datetime.utcnow(),
        'is_read': False
    }
    messages_db[message_id] = new_message
    
    # Update chat
    chat_id = get_or_create_chat(current_user.id, receiver_id)
    chats_db[chat_id]['last_message'] = new_message
    chats_db[chat_id]['unread_count'] += 1
    
    # Notify receiver if online
    if receiver_id in active_connections:
        await active_connections[receiver_id].send_json({
            'type': 'new_message',
            'chat_id': chat_id,
            'message': new_message
        })
    
    return new_message

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
