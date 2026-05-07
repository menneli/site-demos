from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./zenith.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    membership_type = Column(String, default="basic")  # basic, premium, vip
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="user")


class GymClass(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    instructor = Column(String, nullable=False)
    category = Column(String, nullable=False)  # yoga, hiit, pilates, spin, etc.
    duration_minutes = Column(Integer, default=60)
    capacity = Column(Integer, default=20)
    price = Column(Float, default=0.0)
    schedule_time = Column(DateTime, nullable=False)
    location = Column(String, default="Studio A")
    is_active = Column(Boolean, default=True)
    bookings = relationship("Booking", back_populates="gym_class")

    @property
    def spots_left(self):
        confirmed = sum(1 for b in self.bookings if b.status == "confirmed")
        return self.capacity - confirmed


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))
    status = Column(String, default="confirmed")  # confirmed, cancelled
    booked_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="bookings")
    gym_class = relationship("GymClass", back_populates="bookings")


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)