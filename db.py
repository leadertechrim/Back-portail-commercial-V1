from pymongo import MongoClient

def get_db():
    client = MongoClient("mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority")
    return client["appels_doffres_db_copy"]
