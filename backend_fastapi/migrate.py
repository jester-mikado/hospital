import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import Base

SQLITE_URL = "sqlite:///./hospital.db"

POSTGRES_URL = os.getenv("DATABASE_URL")

sqlite_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False}
)

postgres_engine = create_engine(POSTGRES_URL)

SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

Base.metadata.create_all(bind=postgres_engine)

sqlite_db = SQLiteSession()
postgres_db = PostgresSession()

# clear old postgres data safely
for table in [
    models.Appointment,
    models.Slot,
    models.Doctor,
    models.Patient,
    models.User,
]:
    postgres_db.query(table).delete()
    postgres_db.commit()

# migrate independent tables first
for table in [
    models.User,
    models.Patient,
    models.Doctor,
    models.Slot,
]:
    records = sqlite_db.query(table).all()

    for record in records:
        data = record.__dict__.copy()
        data.pop("_sa_instance_state", None)

        postgres_db.merge(table(**data))

    postgres_db.commit()

# migrate appointments only if related slot exists
appointments = sqlite_db.query(models.Appointment).all()

for appointment in appointments:
    slot_exists = postgres_db.query(models.Slot).filter(
        models.Slot.id == appointment.slot_id
    ).first()

    patient_exists = postgres_db.query(models.Patient).filter(
        models.Patient.id == appointment.patient_id
    ).first()

    doctor_exists = postgres_db.query(models.Doctor).filter(
        models.Doctor.id == appointment.doctor_id
    ).first()

    if slot_exists and patient_exists and doctor_exists:
        data = appointment.__dict__.copy()
        data.pop("_sa_instance_state", None)

        postgres_db.merge(models.Appointment(**data))
    else:
        print(
            f"Skipped appointment {appointment.id} "
            f"because slot/patient/doctor missing"
        )

postgres_db.commit()

sqlite_db.close()
postgres_db.close()

print("Migration completed successfully")