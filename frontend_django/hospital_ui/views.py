from django.shortcuts import render, redirect
from django.http import HttpResponse
import requests
from django.core.cache import cache

API_URL = "https://hospital-management-p1pj.onrender.com"

def check_role(request, allowed_role):

    if request.session.get("role") != allowed_role:
        return False

    return True


def landing_page(request):

    doctors = cache.get("landing_doctors")
    reviews = cache.get("landing_reviews")

    try:
        if doctors is None:
            doctors = api_get(f"{API_URL}/doctors")
            cache.set("landing_doctors", doctors, 300)

        if reviews is None:
            reviews = api_get(f"{API_URL}/reviews")
            cache.set("landing_reviews", reviews, 300)

    except requests.exceptions.RequestException:
        doctors = doctors or []
        reviews = reviews or []

    return render(request, "landing.html", {
        "doctors": doctors,
        "reviews": reviews
    })


def login_page(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        response = requests.post(
            f"{API_URL}/login",
            json={
                "username": username,
                "password": password
            }
        )

        if response.status_code == 200:

            data = response.json()

            request.session["user_id"] = data["user_id"]
            request.session["role"] = data["role"]

            if "access_token" in data:
                request.session["token"] = data["access_token"]

            if data["role"] == "admin":
                return redirect("admin_dashboard")

            elif data["role"] == "doctor":
                return redirect("doctor_dashboard")

            else:
                return redirect("patient_dashboard")

        return render(request, "login.html", {
            "error": "Invalid username or password"
        })

    return render(request, "login.html")


# REGISTER
def register_page(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")
        name = request.POST.get("name")
        age = request.POST.get("age")

        if not username or not password or not name or not age:
            return render(request, "register.html", {
                "error": "All fields are required"
            })

        response = requests.post(
            f"{API_URL}/register",
            json={
                "username": username,
                "password": password,
                "name": name,
                "age": int(age)
            }
        )

        if response.status_code == 200:
            return redirect("login")

        return render(request, "register.html", {
            "error": "Username already exists or registration failed"
        })

    return render(request, "register.html")


# PATIENT DASHBOARD
def patient_dashboard(request):

    if not check_role(request, "patient"):
        return redirect("login")

    user_id = request.session.get("user_id")

    data = api_get(
        f"{API_URL}/patient/dashboard-data/{user_id}"
    )

    doctors = data["doctors"]
    appointments = data["appointments"]

    selected_specialist = request.GET.get("specialist")

    if selected_specialist and selected_specialist != "All":
        doctors = [
            doctor for doctor in doctors
            if doctor["specialist"] == selected_specialist
        ]

    return render(request, "patient_dashboard.html", {
        "doctors": doctors,
        "appointments": appointments
    })

def doctor_dashboard(request):

    if not check_role(request, "doctor"):
        return redirect("login")

    user_id = request.session.get("user_id")

    data = api_get(
        f"{API_URL}/doctor/dashboard-data/{user_id}"
    )

    doctor = data["doctor"]
    appointments = data["appointments"]

    appointments = [
        appointment for appointment in appointments
        if appointment["status"] in ["pending", "accepted"]
    ]

    selected_status = request.GET.get("status")

    if selected_status and selected_status != "All":
        appointments = [
            appointment for appointment in appointments
            if appointment["status"] == selected_status
        ]

    return render(request, "doctor_dashboard.html", {
        "appointments": appointments,
        "doctor_id": doctor["id"]
    })
    
def accept_appointment(request, appointment_id):

    token = request.session.get("token")

    requests.put(
        f"{API_URL}/appointments/{appointment_id}/accept",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    return redirect("doctor_dashboard")


def reject_appointment(request, appointment_id):

    token = request.session.get("token")

    requests.put(
        f"{API_URL}/appointments/{appointment_id}/reject",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    return redirect("doctor_dashboard")


def add_slot(request):

    if not check_role(request, "doctor"):
        return redirect("login")

    user_id = request.session.get("user_id")

    data = api_get(
        f"{API_URL}/doctor/dashboard-data/{user_id}"
    )

    doctor = data["doctor"]
    slots = data["slots"]

    doctor_id = doctor["id"]
    specialist = doctor["specialist"]

    if request.method == "POST":

        time = request.POST.get("time")

        response = api_post(
            f"{API_URL}/slots",
            {
                "doctor_id": doctor_id,
                "time": time,
                "specialist": specialist
            }
        )

        if response.status_code != 200:
            return render(request, "add_slot.html", {
                "specialist": specialist,
                "slots": slots,
                "error": "This slot already exists"
            })

        return redirect("doctor_dashboard")

    return render(request, "add_slot.html", {
        "specialist": specialist,
        "slots": slots
    })

def admin_dashboard(request):

    if not check_role(request, "admin"):
        return redirect("login")

    token = request.session.get("token")

    response = requests.get(
        f"{API_URL}/admin/dashboard-data",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=8
    )

    data = response.json()

    return render(request, "admin_dashboard.html", {
        "users": data["users"],
        "appointments": data["appointments"],
        "slots": data["slots"],
        "reviews": data["reviews"]
    })

def doctor_slots(request, doctor_id):

    selected_specialist = request.GET.get("specialist")

    response = requests.get(
        f"{API_URL}/slots/{doctor_id}"
    )

    slots = response.json()

    if selected_specialist and selected_specialist != "All":

        slots = [
            slot for slot in slots
            if slot["specialist"] == selected_specialist
        ]

    return render(request, "slots.html", {
        "slots": slots,
        "doctor_id": doctor_id,
        "selected_specialist": selected_specialist
    })

def book_appointment(request, slot_id, doctor_id):

    slots = requests.get(
        f"{API_URL}/slots/{doctor_id}"
    ).json()

    selected_slot = None

    for slot in slots:
        if slot["id"] == slot_id:
            selected_slot = slot

    specialist = selected_slot["specialist"]

    if request.method == "POST":

        user_id = request.session.get("user_id")

        patient_response = requests.get(
            f"{API_URL}/patient/by-user/{user_id}"
        )

        patient = patient_response.json()
        patient_id = patient["id"]

        patient_name = request.POST.get("name")
        patient_age = request.POST.get("age")
        reason = request.POST.get("reason")

        requests.post(
            f"{API_URL}/book",
            json={
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "slot_id": slot_id,
                "patient_name": patient_name,
                "patient_age": int(patient_age),
                "reason": reason,
                "specialist": specialist
            }
        )

        return redirect("patient_dashboard")

    return render(request, "book.html", {
        "specialist": specialist,
        "slot": selected_slot
    })

def done_appointment(request, appointment_id):

    requests.put(
        f"{API_URL}/appointments/{appointment_id}/done"
    )

    return redirect("review_page", appointment_id=appointment_id)

def home_page(request):

    role = request.session.get("role")

    if role == "admin":
        return redirect("admin_dashboard")

    elif role == "doctor":
        return redirect("doctor_dashboard")

    elif role == "patient":
        return redirect("patient_dashboard")

    return redirect("login")


def logout_page(request):

    request.session.flush()

    return redirect("landing")

def delete_appointment(request, appointment_id):

    if not check_role(request, "admin"):
        return redirect("login")

    token = request.session.get("token")

    response = requests.delete(
        f"{API_URL}/admin/appointments/{appointment_id}",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    print("DELETE STATUS:", response.status_code)
    print("DELETE RESPONSE:", response.text)
    cache.delete("landing_doctors")

    return redirect("admin_dashboard") 

def my_appointments(request):

    if not check_role(request, "patient"):
        return redirect("login")

    user_id = request.session.get("user_id")

    patient_response = requests.get(
        f"{API_URL}/patient/by-user/{user_id}"
    )

    patient = patient_response.json()

    patient_id = patient["id"]

    appointments_response = requests.get(
        f"{API_URL}/patient/appointments/{patient_id}"
    )

    appointments = appointments_response.json()

    # SHOW ONLY ACTIVE APPOINTMENTS
    appointments = [
        appointment for appointment in appointments
        if appointment["status"] in ["pending", "accepted"]
    ]

    return render(request, "my_appointments.html", {
        "appointments": appointments
    })
    
def delete_slot(request, slot_id):

    token = request.session.get("token")

    requests.delete(
        f"{API_URL}/admin/slots/{slot_id}",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
    cache.delete("landing_doctors")

    return redirect("admin_dashboard")

def patient_history(request):

    if not check_role(request, "patient"):
        return redirect("login")

    user_id = request.session.get("user_id")

    patient = requests.get(
        f"{API_URL}/patient/by-user/{user_id}"
    ).json()

    appointments = requests.get(
        f"{API_URL}/patient/appointments/{patient['id']}"
    ).json()

    history = [
        appointment for appointment in appointments
        if appointment["status"] in ["completed", "denied"]
    ]

    return render(request, "patient_history.html", {
        "history": history
    })


def doctor_history(request):

    if not check_role(request, "doctor"):
        return redirect("login")

    user_id = request.session.get("user_id")

    doctor = requests.get(
        f"{API_URL}/doctor/by-user/{user_id}"
    ).json()

    appointments = requests.get(
        f"{API_URL}/doctor/appointments/{doctor['id']}"
    ).json()

    history = [
        appointment for appointment in appointments
        if appointment["status"] in ["completed", "denied"]
    ]

    return render(request, "doctor_history.html", {
        "history": history
    })

def review_page(request, appointment_id):

    if not check_role(request, "patient"):
        return redirect("login")

    user_id = request.session.get("user_id")

    patient = requests.get(
        f"{API_URL}/patient/by-user/{user_id}"
    ).json()

    appointments = requests.get(
        f"{API_URL}/patient/appointments/{patient['id']}"
    ).json()

    selected_appointment = None

    for appointment in appointments:
        if appointment["id"] == appointment_id:
            selected_appointment = appointment
    if selected_appointment is None:
        return redirect("patient_history")

    doctors = requests.get(
        f"{API_URL}/doctors"
    ).json()

    doctor_name = ""

    for doctor in doctors:
        if doctor["id"] == selected_appointment["doctor_id"]:
            doctor_name = doctor["name"]

    if request.method == "POST":

        rating = request.POST.get("rating")
        review_text = request.POST.get("review_text")

        response = requests.post(
            f"{API_URL}/reviews",
            json={
                "appointment_id": appointment_id,
                "patient_id": patient["id"],
                "doctor_id": selected_appointment["doctor_id"],
                "patient_name": selected_appointment["patient_name"],
                "doctor_name": doctor_name,
                "specialist": selected_appointment["specialist"],
                "rating": int(rating),
                "review_text": review_text
            }
        )
        if response.status_code == 200:
            cache.delete("landing_reviews")

        return redirect("patient_history")

    return render(request, "review.html", {
        "appointment": selected_appointment,
        "doctor_name": doctor_name
    })

def delete_review(request, review_id):

    if not check_role(request, "admin"):
        return redirect("login")

    token = request.session.get("token")

    requests.delete(
        f"{API_URL}/admin/reviews/{review_id}",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
    cache.delete("landing_doctors")

    return redirect("admin_dashboard")

def api_get(url):
    return requests.get(url, timeout=30).json()


def api_post(url, data):
    return requests.post(url, json=data, timeout=30)


def api_put(url):
    return requests.put(url, timeout=30)


def api_delete(url, headers=None):
    return requests.delete(url, headers=headers, timeout=30)