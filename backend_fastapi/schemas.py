from pydantic import BaseModel


class RegisterUser(BaseModel):
    username: str
    password: str
    name: str
    age: int


class LoginUser(BaseModel):
    username: str
    password: str


class PromoteDoctor(BaseModel):
    user_id: int
    specialist: str


class SlotCreate(BaseModel):
    doctor_id: int
    time: str
    specialist: str


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    slot_id: int
    patient_name: str
    patient_age: int
    reason: str
    specialist: str