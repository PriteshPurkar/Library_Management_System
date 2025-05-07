from pymongo import MongoClient
from bson import ObjectId
import datetime

# MongoDB Atlas connection string
client = MongoClient("mongodb+srv://pritesh:pritesh%4017@cluster0.lkpjjfb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Select database and collections
db = client["LibraryDB"]
students = db["Students"]
books = db["Books"]
transactions = db["Transactions"]

# Clear existing data (optional)
# students.delete_many({})
# books.delete_many({})
# transactions.delete_many({})

# Insert sample student
student_id = students.insert_one({
    "rfid": "STU12345",
    "name": "Alice Sharma",
    "phone": "+919876543210",
    "email": "alice.sharma@example.com"
}).inserted_id

print(f"✅ Inserted student with ID: {student_id}")

# Insert sample book
book_id = books.insert_one({
    "rfid": "BOOK98765",
    "title": "Clean Code",
    "author": "Robert C. Martin"
}).inserted_id

print(f"✅ Inserted book with ID: {book_id}")

# Insert sample transaction (issued book)
transactions.insert_one({
    "student_id": student_id,
    "book_id": book_id,
    "issued_on": datetime.datetime.now(),
    "due_date": datetime.datetime.now() + datetime.timedelta(days=15),
    "status": "issued"
})

print("📚 Sample transaction (issued) inserted successfully!")
