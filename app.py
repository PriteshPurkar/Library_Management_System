from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from twilio.rest import Client
import datetime

app = Flask(__name__)

# *MongoDB Atlas Connection*
client = MongoClient("mongodb+srv://pritesh:pritesh%4017@cluster0.lkpjjfb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["LibraryDB"]
students = db["Students"]
books = db["Books"]
transactions = db["Transactions"]

# *Twilio Credentials*
TWILIO_SID = "ACed158209e4f69aeb47022396e538dd91"
TWILIO_AUTH_TOKEN = "f35e020eef98ab74e5025705e214185a"
TWILIO_PHONE_NUMBER = "+14155238886"

# *Latest RFID Scan*
latest_scan = None  

@app.route('/')
def home():
    return render_template("index.html")


def send_whatsapp_notification(phone_number, message):
    """ Send WhatsApp notification using Twilio """
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        from_="whatsapp:" + TWILIO_PHONE_NUMBER,
        body=message,
        to="whatsapp:" + phone_number
    )


@app.route('/receive_rfid', methods=['POST'])
def receive_rfid():
    """ Receive and process RFID scan """
    global latest_scan
    data = request.json
    rfid = data.get("rfid")

    student = students.find_one({"rfid": rfid})
    book = books.find_one({"rfid": rfid})

    if student:
        latest_scan = {
            "type": "student",
            "student_id": str(student["_id"]),
            "name": student["name"]
        }
    elif book:
        latest_scan = {
            "type": "book",
            "book_id": str(book["_id"]),
            "title": book["title"]
        }
    else:
        latest_scan = {"type": "unknown"}  # Prevent getting stuck

    return jsonify({"message": "RFID received"}), 200


@app.route('/wait_for_rfid', methods=['GET'])
def wait_for_rfid():
    """ Check for a new RFID scan """
    global latest_scan
    if latest_scan:
        response = latest_scan
        latest_scan = None  # Reset after sending
        return jsonify(response)
    return jsonify({"type": "waiting"})


@app.route('/process_transaction', methods=['POST'])
def process_transaction():
    """ Process Issue, Return, and Renew Transactions """
    data = request.json
    student_id = data.get("student_id")
    book_id = data.get("book_id")
    action = data.get("action")

    student = students.find_one({"_id": student_id})
    book = books.find_one({"_id": book_id})

    if not student or not book:
        return jsonify({"error": "Invalid student or book"}), 400

    phone_number = student["phone"]
    student_name = student["name"]
    book_name = book["title"]

    if action == "issue":
        # Check if the book is already issued
        existing_issue = transactions.find_one({"book_id": book_id, "status": "issued"})
        if existing_issue:
            return jsonify({"error": "This book is already issued to another student."}), 400

        due_date = datetime.datetime.now() + datetime.timedelta(days=15)
        transactions.insert_one({
            "student_id": student_id,
            "book_id": book_id,
            "issued_on": datetime.datetime.now(),
            "due_date": due_date,
            "status": "issued"
        })
        message = f"📚 *Library Notification*\n\n✅ *Book Issued*\n📖 Book: {book_name}\n👤 Student: {student_name}\n📅 Due Date: {due_date.strftime('%d-%m-%Y')}\n\nPlease return it on time!"
        send_whatsapp_notification(phone_number, message)

    elif action == "return":
        update_result = transactions.update_one(
            {"student_id": student_id, "book_id": book_id, "status": "issued"},
            {"$set": {"status": "returned", "returned_on": datetime.datetime.now()}}
        )
        if update_result.modified_count == 0:
            return jsonify({"error": "Return failed. The book might not be issued to this student."}), 400

        message = f"📚 *Library Notification*\n\n🔄 *Book Returned*\n📖 Book: {book_name}\n👤 Student: {student_name}\n📅 Returned on: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n\nThank you!"
        send_whatsapp_notification(phone_number, message)

    elif action == "renew":
        new_due_date = datetime.datetime.now() + datetime.timedelta(days=15)
        update_result = transactions.update_one(
            {"student_id": student_id, "book_id": book_id, "status": "issued"},
            {"$set": {"due_date": new_due_date}}
        )
        
        if update_result.modified_count == 0:
            return jsonify({"error": "Renewal failed. Book might not be issued."}), 400

        message = f"📚 *Library Notification*\n\n🔄 *Book Renewed*\n📖 Book: {book_name}\n👤 Student: {student_name}\n📅 New Due Date: {new_due_date.strftime('%d-%m-%Y')}\n\nEnjoy your reading!"
        send_whatsapp_notification(phone_number, message)

    return jsonify({"message": f"{action.capitalize()} successful"}), 200


@app.route('/exit_rfid_scan', methods=['POST'])
def exit_rfid_scan():
    """Check the latest transaction status of the book before allowing exit."""
    data = request.json
    book_rfid = data.get("rfid")

    book = books.find_one({"rfid": book_rfid})
    if not book:
        return jsonify({"error": "Book not found in database"}), 404  # Book is not registered in the system

    # Fetch the latest transaction for this book
    latest_transaction = transactions.find_one(
        {"book_id": str(book["_id"])},
        sort=[("issued_on", -1)]  # Get the most recent transaction
    )

    # If no transaction record exists, treat it as possible theft
    if not latest_transaction:
        return jsonify({"error": "No transaction history found! Possible theft!"}), 403  

    # Check if the latest transaction is "issued" or "renewed"
    if latest_transaction["status"] in ["issued", "renewed"]:
        return jsonify({"message": "Book is currently issued, exit allowed."}), 200
    else:
        return jsonify({"error": "Book was returned! Possible theft detected!"}), 403


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)