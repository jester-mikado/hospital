from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("patient/", views.patient_dashboard, name="patient_dashboard"),
    path("doctor/", views.doctor_dashboard, name="doctor_dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("doctor-slots/<int:doctor_id>/", views.doctor_slots, name="doctor_slots"),
    path("book/<int:slot_id>/<int:doctor_id>/", views.book_appointment, name="book_appointment"),
    path("accept/<int:appointment_id>/", views.accept_appointment, name="accept_appointment"),
    path("reject/<int:appointment_id>/", views.reject_appointment, name="reject_appointment"),
    path("add-slot/", views.add_slot, name="add_slot"),
    path("done/<int:appointment_id>/", views.done_appointment),
    path("logout/", views.logout_page, name="logout"),
    path("home/", views.home_page, name="home"),
    path("admin/delete-appointment/<int:appointment_id>/", views.delete_appointment),
    path("my-appointments/", views.my_appointments),
    path("admin/delete-slot/<int:slot_id>/", views.delete_slot),
    path("doctor-history/", views.doctor_history, name="doctor_history"),
    path("patient-history/", views.patient_history, name="patient_history"),
]
