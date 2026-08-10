from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from database import engine, SessionLocal
from auth import hash_password, verify_password, create_token, admin_required, doctor_required


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.on_event("startup")
def startup_event():

    db = SessionLocal()

    try:
        create_default_admin(db)

    finally:
        db.close()

def create_default_admin(db):

    admin = db.query(models.User).filter(
        models.User.username == "admin"
    ).first()

    if not admin:

        new_admin = models.User(
            username="admin",
            password=hash_password("admin123"),
            role="admin"
        )
        db.add(new_admin)
        db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home(db: Session = Depends(get_db)):
    create_default_admin(db)
    return {"message": "Hospital FastAPI Backend Running"}


@app.post("/register")
def register(user: schemas.RegisterUser, db: Session = Depends(get_db)):

    existing = db.query(models.User).filter(
        models.User.username == user.username
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = models.User(
        username=user.username,
        password=hash_password(user.password),
        role="patient"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    patient = models.Patient(
        name=user.name,
        age=user.age,
        user_id=new_user.id
    )

    db.add(patient)
    db.commit()

    return {"message": "Patient registered successfully"}

@app.put("/admin/promote-doctor")
def promote_to_doctor(
    data: schemas.PromoteDoctor,
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_required)
):

    user = db.query(models.User).filter(
        models.User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot be changed")

    patient = db.query(models.Patient).filter(
        models.Patient.user_id == user.id
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    existing_doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == user.id
    ).first()

    user.role = "doctor"

    if existing_doctor:
        existing_doctor.specialist = data.specialist
        existing_doctor.name = patient.name
    else:
        doctor = models.Doctor(
            name=patient.name,
            specialist=data.specialist,
            user_id=user.id
        )
        db.add(doctor)

    db.commit()

    return {"message": "Doctor promoted/updated successfully"}

@app.post("/login")
def login(user: schemas.LoginUser, db: Session = Depends(get_db)):

    db_user = db.query(models.User).filter(
        models.User.username == user.username
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Wrong password")

    # Patient login
    if db_user.role == "patient":
        return {
            "message": "Patient login successful",
            "role": db_user.role,
            "user_id": db_user.id
        }

    # Doctor/Admin login with token
    token = create_token({
        "id": db_user.id,
        "username": db_user.username,
        "role": db_user.role
    })

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "role": db_user.role,
        "user_id": db_user.id
    }

@app.post("/slots")
def add_slot(slot: schemas.SlotCreate, db: Session = Depends(get_db)):

    existing_slot = db.query(models.Slot).filter(
        models.Slot.doctor_id == slot.doctor_id,
        models.Slot.time == slot.time,
        models.Slot.specialist == slot.specialist
    ).first()

    if existing_slot:
        raise HTTPException(
            status_code=400,
            detail="This slot already exists for this doctor"
        )

    new_slot = models.Slot(
        doctor_id=slot.doctor_id,
        time=slot.time,
        specialist=slot.specialist,
        status="available"
    )

    db.add(new_slot)
    db.commit()

    return {"message": "Slot added successfully"}


@app.get("/doctors")
def get_doctors(db: Session = Depends(get_db)):
    return db.query(models.Doctor).all()


@app.get("/slots/{doctor_id}")
def get_slots(doctor_id: int, db: Session = Depends(get_db)):

    return db.query(models.Slot).filter(
        models.Slot.doctor_id == doctor_id
    ).all()


@app.post("/book")
def book_appointment(
    appointment: schemas.AppointmentCreate,
    db: Session = Depends(get_db)
):

    slot = db.query(models.Slot).filter(
        models.Slot.id == appointment.slot_id
    ).first()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if slot.status == "booked":
        raise HTTPException(status_code=400, detail="Slot already booked")

    new_appointment = models.Appointment(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        slot_id=appointment.slot_id,
        patient_name=appointment.patient_name,
        patient_age=appointment.patient_age,
        reason=appointment.reason,
        specialist=appointment.specialist,
        status="pending"
    )

    slot.status = "booked"

    db.add(new_appointment)
    db.commit()

    return {"message": "Appointment booked and pending doctor approval"}


@app.get("/doctor/appointments/{doctor_id}")
def doctor_appointments(doctor_id: int, db: Session = Depends(get_db)):

    return db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id
    ).all()


@app.get("/patient/appointments/{patient_id}")
def patient_appointments(patient_id: int, db: Session = Depends(get_db)):

    return db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient_id
    ).all()


@app.put("/appointments/{appointment_id}/accept")
def accept_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(doctor_required)
):

    appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = "accepted"

    db.commit()

    return {"message": "Appointment accepted"}

@app.put("/appointments/{appointment_id}/reject")
def reject_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(doctor_required)
):

    appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = "denied"

    db.commit()

    return {"message": "Appointment denied"}

@app.put("/appointments/{appointment_id}/done")
def complete_appointment(appointment_id: int, db: Session = Depends(get_db)):

    appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = "completed"

    slot = db.query(models.Slot).filter(
        models.Slot.id == appointment.slot_id
    ).first()

    if slot:
        slot.status = "available"

    db.commit()

    return {"message": "Appointment completed"}


@app.get("/admin/users")
def admin_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@app.get("/admin/appointments")
def admin_appointments(db: Session = Depends(get_db)):
    return db.query(models.Appointment).all()


@app.delete("/admin/appointments/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_required)
):

    appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    db.delete(appointment)
    db.commit()

    return {"message": "Appointment deleted"}

@app.delete("/admin/doctors/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_required)
):

    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    db.delete(doctor)
    db.commit()

    return {"message": "Doctor deleted"}

@app.get("/patient/by-user/{user_id}")
def get_patient_by_user(user_id: int, db: Session = Depends(get_db)):

    patient = db.query(models.Patient).filter(
        models.Patient.user_id == user_id
    ).first()

    return patient

@app.get("/doctor/by-user/{user_id}")
def get_doctor_by_user(user_id: int, db: Session = Depends(get_db)):

    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == user_id
    ).first()

    return doctor

@app.delete("/admin/delete-empty-doctors")
def delete_empty_doctors(db: Session = Depends(get_db)):

    empty_doctors = db.query(models.Doctor).filter(
        models.Doctor.name == ""
    ).all()

    for doctor in empty_doctors:
        db.delete(doctor)

    db.commit()

    return {"message": "Empty doctors deleted"}

@app.get("/admin/slots")
def admin_slots(db: Session = Depends(get_db)):
    return db.query(models.Slot).all()


@app.delete("/admin/slots/{slot_id}")
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_required)
):

    slot = db.query(models.Slot).filter(
        models.Slot.id == slot_id
    ).first()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    db.delete(slot)
    db.commit()

    return {"message": "Slot deleted"}

@app.get("/reviews")
def get_reviews(db: Session = Depends(get_db)):
    return db.query(models.Review).all()

@app.post("/reviews")
def create_review(
    review: schemas.ReviewCreate,
    db: Session = Depends(get_db)
):

    print(review)

    existing_review = db.query(models.Review).filter(
        models.Review.appointment_id == review.appointment_id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="Review already submitted for this appointment"
        )

    new_review = models.Review(
        appointment_id=review.appointment_id,
        patient_id=review.patient_id,
        doctor_id=review.doctor_id,
        patient_name=review.patient_name,
        doctor_name=review.doctor_name,
        specialist=review.specialist,
        rating=review.rating,
        review_text=review.review_text
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return {
        "message": "Review submitted successfully",
        "review_id": new_review.id
    }


@app.delete("/admin/reviews/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_required)
):

    review = db.query(models.Review).filter(
        models.Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()

    return {"message": "Review deleted successfully"}

@app.get("/admin/dashboard-data")
def admin_dashboard_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(admin_required)
):

    users = db.query(models.User).all()
    appointments = db.query(models.Appointment).all()
    slots = db.query(models.Slot).all()
    reviews = db.query(models.Review).all()

    return {
        "users": users,
        "appointments": appointments,
        "slots": slots,
        "reviews": reviews
    }

@app.get("/patient/dashboard-data/{user_id}")
def patient_dashboard_data(
    user_id: int,
    db: Session = Depends(get_db)
):

    patient = db.query(models.Patient).filter(
        models.Patient.user_id == user_id
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctors = db.query(models.Doctor).all()

    appointments = db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient.id
    ).all()

    return {
        "patient": patient,
        "doctors": doctors,
        "appointments": appointments
    }

@app.get("/doctor/dashboard-data/{user_id}")
def doctor_dashboard_data(
    user_id: int,
    db: Session = Depends(get_db)
):

    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == user_id
    ).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.id
    ).all()

    slots = db.query(models.Slot).filter(
        models.Slot.doctor_id == doctor.id
    ).all()

    return {
        "doctor": doctor,
        "appointments": appointments,
        "slots": slots
    }
@app.get("/health")
async def health():
    return {"status": "ok"}
