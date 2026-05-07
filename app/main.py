from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import get_db, init_db, User, GymClass, Booking, ContactMessage
from app.auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_user, require_admin
)

app = FastAPI(title="Zenith")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()


def base_ctx(request: Request, db: Session, **kwargs):
    user = get_current_user(request, db)
    return {"request": request, "current_user": user, "now": datetime.now(), **kwargs}


# ─── HOME ───

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    upcoming = (
        db.query(GymClass)
        .filter(GymClass.schedule_time >= datetime.now(), GymClass.is_active == True)
        .order_by(GymClass.schedule_time)
        .limit(3)
        .all()
    )
    return templates.TemplateResponse("home.html", base_ctx(request, db, upcoming=upcoming))


# ─── AUTH ───

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", base_ctx(request, db))


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", base_ctx(request, db, error="Invalid email or password")
        )
    token = create_token({"sub": str(user.id)})
    response = RedirectResponse("/schedule", status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24 * 7)
    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("register.html", base_ctx(request, db))


@app.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            "register.html", base_ctx(request, db, error="Email already registered")
        )
    user = User(name=name, email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    token = create_token({"sub": str(user.id)})
    response = RedirectResponse("/schedule", status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24 * 7)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("access_token")
    return response


# ─── SCHEDULE & BOOKING ───

@app.get("/schedule", response_class=HTMLResponse)
def schedule(
    request: Request,
    category: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(GymClass).filter(
        GymClass.schedule_time >= datetime.now(),
        GymClass.is_active == True,
    )
    if category:
        q = q.filter(GymClass.category == category)
    classes = q.order_by(GymClass.schedule_time).all()

    user = get_current_user(request, db)
    user_booking_ids = set()
    if user:
        user_booking_ids = {
            b.class_id for b in db.query(Booking).filter(
                Booking.user_id == user.id, Booking.status == "confirmed"
            ).all()
        }
    categories = db.query(GymClass.category).distinct().all()
    categories = [c[0] for c in categories]
    return templates.TemplateResponse(
        "schedule.html",
        base_ctx(request, db, classes=classes, categories=categories,
                 selected_cat=category, user_booking_ids=user_booking_ids)
    )


@app.post("/book/{class_id}")
def book_class(class_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    gc = db.query(GymClass).filter(GymClass.id == class_id).first()
    if not gc:
        raise HTTPException(404)

    existing = db.query(Booking).filter(
        Booking.user_id == user.id,
        Booking.class_id == class_id,
        Booking.status == "confirmed",
    ).first()
    if existing:
        return RedirectResponse("/schedule?msg=already_booked", status_code=302)

    if gc.spots_left <= 0:
        return RedirectResponse("/schedule?msg=full", status_code=302)

    booking = Booking(user_id=user.id, class_id=class_id)
    db.add(booking)
    db.commit()
    return RedirectResponse("/my-bookings?msg=booked", status_code=302)


@app.post("/cancel/{booking_id}")
def cancel_booking(booking_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    booking = db.query(Booking).filter(
        Booking.id == booking_id, Booking.user_id == user.id
    ).first()
    if booking:
        booking.status = "cancelled"
        db.commit()
    return RedirectResponse("/my-bookings", status_code=302)


@app.get("/my-bookings", response_class=HTMLResponse)
def my_bookings(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user.id, Booking.status == "confirmed")
        .join(GymClass)
        .order_by(GymClass.schedule_time)
        .all()
    )
    return templates.TemplateResponse(
        "my_bookings.html", base_ctx(request, db, bookings=bookings)
    )


# ─── CONTACT ───

@app.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("contact.html", base_ctx(request, db))


@app.post("/contact")
def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(""),
    message: str = Form(...),
    db: Session = Depends(get_db),
):
    msg = ContactMessage(name=name, email=email, subject=subject, message=message)
    db.add(msg)
    db.commit()
    return templates.TemplateResponse(
        "contact.html", base_ctx(request, db, success=True)
    )


# ─── ADMIN ───

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse("/login", status_code=302)

    stats = {
        "total_users": db.query(User).count(),
        "total_classes": db.query(GymClass).count(),
        "total_bookings": db.query(Booking).filter(Booking.status == "confirmed").count(),
        "unread_messages": db.query(ContactMessage).filter(ContactMessage.is_read == False).count(),
    }
    recent_bookings = (
        db.query(Booking).order_by(Booking.booked_at.desc()).limit(8).all()
    )
    messages = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(5).all()
    classes = db.query(GymClass).order_by(GymClass.schedule_time).limit(10).all()
    return templates.TemplateResponse(
        "dashboard.html",
        base_ctx(request, db, stats=stats, recent_bookings=recent_bookings,
                 messages=messages, classes=classes)
    )


@app.post("/admin/classes/add")
def admin_add_class(
    request: Request,
    title: str = Form(...),
    instructor: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    schedule_time: str = Form(...),
    duration_minutes: int = Form(60),
    capacity: int = Form(20),
    price: float = Form(0.0),
    location: str = Form("Studio A"),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        raise HTTPException(403)
    gc = GymClass(
        title=title, instructor=instructor, category=category,
        description=description,
        schedule_time=datetime.fromisoformat(schedule_time),
        duration_minutes=duration_minutes, capacity=capacity,
        price=price, location=location,
    )
    db.add(gc)
    db.commit()
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/classes/delete/{class_id}")
def admin_delete_class(class_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        raise HTTPException(403)
    gc = db.query(GymClass).filter(GymClass.id == class_id).first()
    if gc:
        gc.is_active = False
        db.commit()
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/messages/read/{msg_id}")
def mark_message_read(msg_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        raise HTTPException(403)
    msg = db.query(ContactMessage).filter(ContactMessage.id == msg_id).first()
    if msg:
        msg.is_read = True
        db.commit()
    return RedirectResponse("/admin", status_code=302)