from pathlib import Path
import mimetypes
import sqlite3
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, url_for

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB per upload
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)


def get_db():
    conn = sqlite3.connect(BASE_DIR / "vestra.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT 'Other',
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                occasion TEXT NOT NULL DEFAULT 'Everyday',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS outfit_items (
                outfit_id INTEGER NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                PRIMARY KEY (outfit_id, item_id)
            );
        """)
        item_columns = {row[1] for row in db.execute("PRAGMA table_info(items)")}
        if "image_data" not in item_columns:
            db.execute("ALTER TABLE items ADD COLUMN image_data BLOB")
        if "image_mime" not in item_columns:
            db.execute("ALTER TABLE items ADD COLUMN image_mime TEXT")
        legacy_images = db.execute(
            "SELECT id, image FROM items WHERE image IS NOT NULL AND image_data IS NULL"
        ).fetchall()
        for row in legacy_images:
            image_path = UPLOAD_DIR / row["image"]
            if image_path.is_file():
                image_data = image_path.read_bytes()
                image_mime = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
                db.execute(
                    "UPDATE items SET image_data = ?, image_mime = ? WHERE id = ?",
                    (image_data, image_mime, row["id"]),
                )
        count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        if count == 0:
            samples = [
                ("Classic blazer", "Outerwear", "Beige", None),
                ("Everyday sweater", "Tops", "Cream", None),
                ("Straight-fit jeans", "Bottoms", "Blue", None),
                ("Leather tote", "Accessories", "Black", None),
                ("White sneakers", "Footwear", "White", None),
            ]
            db.executemany("INSERT INTO items (name, category, color, image) VALUES (?, ?, ?, ?)", samples)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def serialize_item(row):
    item = dict(row)
    if item.get("image_data") is not None:
        item["image"] = url_for("item_image", item_id=item["id"])
    elif item.get("image"):
        item["image"] = url_for("uploaded_file", filename=item["image"])
    item.pop("image_data", None)
    item.pop("image_mime", None)
    return item


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.get("/api/items/<int:item_id>/image")
def item_image(item_id):
    with get_db() as db:
        item = db.execute("SELECT image_data, image_mime FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None or item["image_data"] is None:
        return jsonify({"error": "Image not found."}), 404
    return Response(item["image_data"], mimetype=item["image_mime"] or "application/octet-stream")


@app.get("/api/items")
def get_items():
    with get_db() as db:
        rows = db.execute("SELECT * FROM items ORDER BY id DESC").fetchall()
    return jsonify([serialize_item(row) for row in rows])


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
        image_data = image.read()
        image_mime = image.mimetype or mimetypes.guess_type(image.filename)[0] or "application/octet-stream"

    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO items (name, category, color, image_data, image_mime) VALUES (?, ?, ?, ?, ?)",
            (name, category, color, image_data, image_mime),
        )
        item = db.execute("SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(serialize_item(item)), 201


@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    with get_db() as db:
        item = db.execute("SELECT image FROM items WHERE id = ?", (item_id,)).fetchone()
        if item is None:
            return jsonify({"error": "Item not found."}), 404
        db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    if item["image"]:
        (UPLOAD_DIR / item["image"]).unlink(missing_ok=True)
    return jsonify({"success": True})


@app.get("/api/outfits")
def get_outfits():
    with get_db() as db:
        outfits = db.execute("SELECT * FROM outfits ORDER BY id DESC").fetchall()
        result = []
        for outfit in outfits:
            items = db.execute("""
                SELECT i.* FROM items i
                JOIN outfit_items oi ON oi.item_id = i.id
                WHERE oi.outfit_id = ? ORDER BY i.id
            """, (outfit["id"],)).fetchall()
            result.append({**dict(outfit), "items": [serialize_item(item) for item in items]})
    return jsonify(result)


@app.post("/api/outfits")
def add_outfit():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    occasion = str(data.get("occasion", "Everyday")).strip() or "Everyday"
    item_ids = data.get("item_ids", [])
    if not name or not isinstance(item_ids, list) or not item_ids:
        return jsonify({"error": "Add an outfit name and select at least one item."}), 400
    try:
        item_ids = list(dict.fromkeys(int(item_id) for item_id in item_ids))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid clothing selection."}), 400

    with get_db() as db:
        existing = db.execute(
            f"SELECT id FROM items WHERE id IN ({','.join('?' for _ in item_ids)})", item_ids
        ).fetchall()
        if len(existing) != len(item_ids):
            return jsonify({"error": "One or more selected items no longer exist."}), 400
        cursor = db.execute("INSERT INTO outfits (name, occasion) VALUES (?, ?)", (name, occasion))
        outfit_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO outfit_items (outfit_id, item_id) VALUES (?, ?)",
            [(outfit_id, item_id) for item_id in item_ids],
        )
    return jsonify({"success": True, "id": outfit_id}), 201


@app.delete("/api/outfits/<int:outfit_id>")
def delete_outfit(outfit_id):
    with get_db() as db:
        cursor = db.execute("DELETE FROM outfits WHERE id = ?", (outfit_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Outfit not found."}), 404
    return jsonify({"success": True})


@app.get("/api/stats")
def stats():
    with get_db() as db:
        items = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        outfits = db.execute("SELECT COUNT(*) FROM outfits").fetchone()[0]
        categories = db.execute("SELECT COUNT(DISTINCT category) FROM items").fetchone()[0]
    return jsonify({"items": items, "outfits": outfits, "categories": categories})


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Image is too large. Maximum size is 5 MB."}), 413


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
