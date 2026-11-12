from datetime import datetime
import os
from urllib.parse import quote_plus
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB connection
uri = os.environ.get("MONGODB_URI")
if not uri:
    user = os.environ.get("MONGO_USERNAME")
    pwd = os.environ.get("MONGO_PASSWORD")
    host = os.environ.get("MONGO_HOST", "mongodb-service")
    port = os.environ.get("MONGO_PORT", "27017")
    db_name = os.environ.get("MONGO_DB", "flask_db")
    auth_src = os.environ.get("MONGO_AUTH_SOURCE", "admin")

    if user and pwd:
        uri = f"mongodb://{quote_plus(user)}:{quote_plus(pwd)}@{host}:{port}/{db_name}?authSource={auth_src}"
    else:
        uri = f"mongodb://{host}:{port}/{db_name}"

client = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = client.flask_db
collection = db.data


@app.route('/')
def index():
    return f"Welcome to the Flask app! The current time is: {datetime.now()}"


@app.route('/data', methods=['GET', 'POST'])
def data():
    if request.method == 'POST':
        item = request.get_json()
        if not item:
            return jsonify({"error": "invalid json"}), 400
        collection.insert_one(item)
        return jsonify({"status": "Data inserted"}), 201

    elif request.method == 'GET':
        docs = list(collection.find({}, {"_id": 0}))
        return jsonify(docs), 200


@app.route('/healthz')
def healthz():
    try:
        client.admin.command('ping')
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
