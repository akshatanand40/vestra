import os
from datetime import datetime, timezone

from bson import Binary, ObjectId
from flask import Flask, Response, jsonify, render_template, request, url_for
from pymongo import DESCENDING, MongoClient


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "vestra")
mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000) if MONGODB_URI else None
mongo_db = mongo_client[MONGODB_DATABASE] if mongo_client else None


def get_db():
    if mongo_db is None:
        raise RuntimeError("MONGODB_URI is not set. Add your MongoDB Atlas connection string.")
    return mongo_db


def init_db():
    """Add the starter wardrobe once when a new MongoDB database is first used."""
    if mongo_db is None:
        return

    items = mongo_db["items"]
    if items.count_documents({}) == 0:
        sample_items = [
            {"name": "Classic blazer", "category": "Outerwear", "color": "Beige"},
            {"name": "Everyday sweater", "category": "Tops", "color": "Cream"},
            {"name": "Straight-fit jeans", "category": "Bottoms", "color": "Blue"},
            {"name": "Leather tote", "category": "Accessories", "color": "Black"},
            {"name": "White sneakers", "category": "Footwear", "color": "White"},
        ]
        now = datetime.now(timezone.utc)
        items.insert_many([
            {**item, "image_data": None, "image_mime": None, "created_at": now}
            for item in sample_items
        ])


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_object_id(value):
    return ObjectId(value) if ObjectId.is_valid(value) else None


def serialize_item(document):
    return {
        "id": str(document["_id"]),
        "name": document["name"],
        "category": document["category"],
        "color": document.get("color", "Other"),
        "image": (
            url_for("item_image", item_id=str(document["_id"]))
            if document.get("image_data") is not None
            else None
        ),
        "created_at": document["created_at"].isoformat(),
    }


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/items/<item_id>/image")
def item_image(item_id):
    object_id = parse_object_id(item_id)
    if object_id is None:
        return jsonify({"error": "Image not found."}), 404

    item = get_db()["items"].find_one(
        {"_id": object_id}, {"image_data": 1, "image_mime": 1}
    )
    if item is None or item.get("image_data") is None:
        return jsonify({"error": "Image not found."}), 404

    return Response(
        bytes(item["image_data"]),
        mimetype=item.get("image_mime") or "application/octet-stream",
    )


@app.get("/api/items")
def get_items():
    documents = get_db()["items"].find().sort("_id", DESCENDING)
    return jsonify([serialize_item(document) for document in documents])


@app.post("/api/items")
def add_item():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    color = request.form.get("color", "Other").strip() or "Other"
    if not name or not category:
        return jsonify({"error": "Please enter an item name and category."}), 400

    image_data = None
    image_mime = None
    image = request.files.get("image")
    if image and image.filename:
        if not allowed_file(image.filename):
            return jsonify({"error": "Use a PNG, JPG, JPEG, WEBP or GIF image."}), 400
        image_data = Binary(image.read())
        image_mime = image.mimetype or "application/octet-stream"

    document = {
        "name": name,
        "category": category,
        "color": color,
        "image_data": image_data,
        "image_mime": image_mime,
        "created_at": datetime.now(timezone.utc),
    }
    result = get_db()["items"].insert_one(document)
    document["_id"] = result.inserted_id
    return jsonify(serialize_item(document)), 201


@app.delete("/api/items/<item_id>")
def delete_item(item_id):
    object_id = parse_object_id(item_id)
    if object_id is None:
        return jsonify({"error": "Item not found."}), 404

    db = get_db()
    result = db["items"].delete_one({"_id": object_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Item not found."}), 404

    # Remove references so deleted items disappear from saved outfits too.
    db["outfits"].update_many({"item_ids": object_id}, {"$pull": {"item_ids": object_id}})
    return jsonify({"success": True})


@app.get("/api/outfits")
def get_outfits():
    db = get_db()
    result = []

    for outfit in db["outfits"].find().sort("_id", DESCENDING):
        item_ids = outfit.get("item_ids", [])
        found_items = db["items"].find({"_id": {"$in": item_ids}})
        items_by_id = {item["_id"]: item for item in found_items}
        result.append({
            "id": str(outfit["_id"]),
            "name": outfit["name"],
            "occasion": outfit.get("occasion", "Everyday"),
            "items": [
                serialize_item(items_by_id[item_id])
                for item_id in item_ids
                if item_id in items_by_id
            ],
        })

    return jsonify(result)


@app.post("/api/outfits")
def add_outfit():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    occasion = str(data.get("occasion", "Everyday")).strip() or "Everyday"
    raw_item_ids = data.get("item_ids", [])

    if not name or not isinstance(raw_item_ids, list) or not raw_item_ids:
        return jsonify({"error": "Add an outfit name and select at least one item."}), 400

    if any(not isinstance(item_id, str) for item_id in raw_item_ids):
        return jsonify({"error": "Invalid clothing selection."}), 400

    item_ids = list(dict.fromkeys(parse_object_id(item_id) for item_id in raw_item_ids))
    if any(item_id is None for item_id in item_ids):
        return jsonify({"error": "Invalid clothing selection."}), 400

    db = get_db()
    if db["items"].count_documents({"_id": {"$in": item_ids}}) != len(item_ids):
        return jsonify({"error": "One or more selected items no longer exist."}), 400

    outfit = {
        "name": name,
        "occasion": occasion,
        "item_ids": item_ids,
        "created_at": datetime.now(timezone.utc),
    }
    result = db["outfits"].insert_one(outfit)
    return jsonify({"success": True, "id": str(result.inserted_id)}), 201


@app.delete("/api/outfits/<outfit_id>")
def delete_outfit(outfit_id):
    object_id = parse_object_id(outfit_id)
    if object_id is None:
        return jsonify({"error": "Outfit not found."}), 404

    result = get_db()["outfits"].delete_one({"_id": object_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Outfit not found."}), 404
    return jsonify({"success": True})


@app.get("/api/stats")
def stats():
    db = get_db()
    items = db["items"]
    outfits = db["outfits"]
    return jsonify({
        "items": items.count_documents({}),
        "outfits": outfits.count_documents({}),
        "categories": len(items.distinct("category")),
    })


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Image is too large. Maximum size is 5 MB."}), 413


init_db()


if __name__ == "__main__":
    app.run(debug=True)
