from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
# from .user import User  

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    conversations = relationship(
        "Conversation",
        secondary="conversation_participants",
        back_populates="participants"
    )
    participant_details = relationship("ConversationParticipant", back_populates="user")

# Association table for many-to-many relationship between users and conversations
conversation_participants = Table(
    'conversation_participants',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('conversation_id', Integer, ForeignKey('conversations.id'), primary_key=True),
    Column('is_admin', Boolean, default=False),
    Column('muted', Boolean, default=False),
    Column('left_conversation', Boolean, default=False)
)

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)  # For group chats
    is_group = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    participants = relationship("User", secondary=conversation_participants, back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    participant_details = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'))
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_read = Column(Boolean, default=False)

    # Relationships
    sender = relationship("User", back_populates="sent_messages")
    conversation = relationship("Conversation", back_populates="messages")

class ConversationParticipant(Base):
    __tablename__ = "conversation_participants_details"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    is_admin = Column(Boolean, default=False)
    muted = Column(Boolean, default=False)
    left_conversation = Column(Boolean, default=False)
    last_read_message_id = Column(Integer, ForeignKey('messages.id'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="participant_details")
    conversation = relationship("Conversation", back_populates="participant_details")
