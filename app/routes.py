from flask import Blueprint, request, jsonify, render_template
from app.models import Tutor, Availability, Booking, Student, Notification
from datetime import datetime
from app import db
import pytz

# Define the Blueprint
routes = Blueprint('routes', __name__)

# Home route
@routes.route("/")
def home():
    return render_template("index.html")  # This looks for 'templates/index.html'

@routes.route("/availability", methods=["GET", "POST"])
def manage_availability():
    if request.method == "GET":
        # Do not fetch or pass notifications for GET requests
        return render_template("availability.html")

    if request.method == "POST":
        tutor_id = request.form.get("tutor_id")
        date = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        time_zone = request.form.get("time_zone")

        # Validate tutor
        tutor = Tutor.query.get(tutor_id)
        if not tutor:
            return render_template("availability.html", error="Tutor not found!")

        # Convert start_time and end_time to datetime.time objects
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()

        # Check for conflicts
        existing_availabilities = Availability.query.filter_by(tutor_id=tutor_id, date=date).all()
        for availability in existing_availabilities:
            if not (
                end_time_obj <= availability.start_time or start_time_obj >= availability.end_time
            ):
                # Log the conflict notification but do not fetch all notifications
                notification = Notification(
                    type="conflict",
                    message=f"Conflict detected for Tutor {tutor_id} on {date}: {start_time} - {end_time} overlaps with {availability.start_time} - {availability.end_time}"
                )
                db.session.add(notification)
                db.session.commit()

                return render_template(
                    "availability.html",
                    error=f"Conflict detected and logged: {availability.start_time} to {availability.end_time}"
                )

        # Add new availability
        availability = Availability(
            tutor_id=tutor_id,
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            start_time=start_time_obj,
            end_time=end_time_obj,
            time_zone=time_zone,
        )
        db.session.add(availability)
        db.session.commit()

        return render_template(
            "availability.html", message="Availability added successfully!"
        )

# Retrieve a tutor’s availability
@routes.route("/availability/<int:tutor_id>", methods=["GET"])
def get_availability(tutor_id):
    # Check if the tutor exists
    tutor = Tutor.query.get(tutor_id)
    if not tutor:
        return jsonify({"error": "Tutor not found"}), 404

    # Retrieve the availability for the tutor
    availabilities = Availability.query.filter_by(tutor_id=tutor_id).all()

    # Format the result into a list of dictionaries
    result = [{
        "date": availability.date,
        "start_time": availability.start_time.strftime("%H:%M"),
        "end_time": availability.end_time.strftime("%H:%M"),
        "time_zone": availability.time_zone
    } for availability in availabilities]

    # Render the HTML template with the tutor's information and availability
    return render_template(
        "tutor_availability.html",
        tutor=tutor,
        availabilities=availabilities
    )

@routes.route("/book-slot", methods=["GET", "POST"])
def book_slot():
    if request.method == "POST":
        # Handle the form submission
        student_id = request.form.get("student_id")
        tutor_id = request.form.get("tutor_id")
        date = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        time_zone = request.form.get("time_zone")

        # Validate student and tutor
        student = Student.query.get(student_id)
        tutor = Tutor.query.get(tutor_id)

        if not student:
            return render_template("book_slot.html", error="Student not found!")
        if not tutor:
            return render_template("book_slot.html", error="Tutor not found!")

        # Check for slot conflicts
        booking_time = datetime.strptime(date + " " + start_time, "%Y-%m-%d %H:%M")
        existing_booking = Booking.query.filter_by(
            tutor_id=tutor_id,
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            start_time=datetime.strptime(start_time, "%H:%M").time(),
            end_time=datetime.strptime(end_time, "%H:%M").time()
        ).first()

        if existing_booking:
            return render_template("book_slot.html", error="Slot already booked!")

        # Add new booking
        booking = Booking(
            student_id=student_id,
            tutor_id=tutor_id,
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            start_time=datetime.strptime(start_time, "%H:%M").time(),
            end_time=datetime.strptime(end_time, "%H:%M").time(),
            time_zone=time_zone,
            booking_time=booking_time
        )
        db.session.add(booking)
        db.session.commit()

        # Render the form again with a success message
        return render_template("book_slot.html", message="Booking confirmed!")

    # Render the booking form on GET requests
    return render_template("book_slot.html")

@routes.route("/bookings/<int:student_id>", methods=["GET"])
def get_bookings(student_id):
    # Validate student
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    # Fetch all bookings for the student
    bookings = Booking.query.filter_by(student_id=student_id).all()
    result = [{
        "tutor_name": booking.tutor.name,  # Assuming a relationship is defined
        "date": booking.date.strftime("%Y-%m-%d"),
        "start_time": booking.start_time.strftime("%H:%M"),
        "end_time": booking.end_time.strftime("%H:%M"),
        "status": booking.status
    } for booking in bookings]

    return jsonify(result)


# Log or send notifications for updates
@routes.route("/notifications", methods=["POST"])
def notifications():
    data = request.json
    # Log or process the notification here (e.g., send an email or log to a database)
    # For simplicity, we’ll just return a success response.
    return jsonify({"message": "Notification sent successfully"})

# Time zone conversion utility
@routes.route("/convert-time", methods=["POST"])
def convert_time():
    data = request.json
    try:
        date_time = datetime.fromisoformat(data["date_time"])
        from_tz = pytz.timezone(data["from_time_zone"])
        to_tz = pytz.timezone(data["to_time_zone"])

        # Localize the input time and convert to the target time zone
        localized_time = from_tz.localize(date_time)
        converted_time = localized_time.astimezone(to_tz)

        return jsonify({"converted_time": converted_time.isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
