from app.models import SessionLocal, init_db, User, GymClass, Booking
from app.auth import hash_password
from datetime import datetime, timedelta
import random


def seed():
    init_db()
    db = SessionLocal()

    # Admin user
    if not db.query(User).filter(User.email == "admin@zenith.com").first():
        admin = User(
            name="Admin",
            email="admin@zenith.com",
            hashed_password=hash_password("admin123"),
            is_admin=True,
            membership_type="vip",
        )
        db.add(admin)

    # Demo user
    if not db.query(User).filter(User.email == "demo@zenith.com").first():
        demo = User(
            name="Alex Rivera",
            email="demo@zenith.com",
            hashed_password=hash_password("demo123"),
            membership_type="premium",
        )
        db.add(demo)

    db.commit()

    # Sample classes
    classes_data = [
        ("Morning Vinyasa Flow", "yoga", "Sofia Chen", "Studio A", 60, 15, 18.0),
        ("HIIT Burn", "hiit", "Marcus Webb", "Main Floor", 45, 20, 22.0),
        ("Restorative Yoga", "yoga", "Sofia Chen", "Studio B", 75, 12, 18.0),
        ("Spin & Sweat", "spin", "Jake Torres", "Spin Room", 50, 18, 20.0),
        ("Pilates Core", "pilates", "Nadia Osei", "Studio A", 55, 10, 20.0),
        ("Power Yoga", "yoga", "Sofia Chen", "Studio A", 60, 15, 18.0),
        ("Boxing Fundamentals", "boxing", "Marcus Webb", "Main Floor", 60, 16, 25.0),
        ("Aerial Yoga", "yoga", "Nadia Osei", "Studio B", 60, 8, 30.0),
        ("Meditation & Breathwork", "meditation", "Sofia Chen", "Studio B", 45, 20, 15.0),
        ("Functional Strength", "strength", "Jake Torres", "Main Floor", 60, 20, 22.0),
        ("Yin Yoga", "yoga", "Nadia Osei", "Studio A", 75, 14, 18.0),
        ("Circuit Training", "hiit", "Marcus Webb", "Main Floor", 50, 20, 22.0),
    ]

    if db.query(GymClass).count() == 0:
        base = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
        offsets = [0, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        times = [3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 17, 18]

        for i, (title, cat, instructor, loc, dur, cap, price) in enumerate(classes_data):
            dt = base + timedelta(days=offsets[i], hours=times[i] - 7)
            gc = GymClass(
                title=title,
                description=f"A premium {cat} session designed to challenge and restore. Led by {instructor}.",
                instructor=instructor,
                category=cat,
                duration_minutes=dur,
                capacity=cap,
                price=price,
                schedule_time=dt,
                location=loc,
            )
            db.add(gc)

    db.commit()
    db.close()
    print("Database seeded successfully")
    print("   Admin: admin@zenith.com / admin123")
    print("   Demo:  demo@zenith.com  / demo123")


if __name__ == "__main__":
    seed()