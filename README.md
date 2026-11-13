# VESTRA — Smart Digital Wardrobe

A beginner-friendly Flask + SQLite wardrobe project.

## Features
- View and search wardrobe items
- Filter by clothing category
- Add clothing items with optional image uploads
- Delete wardrobe items
- Create outfits from saved wardrobe pieces
- View and delete saved outfits
- Dashboard counts powered by the database

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment (recommended):
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows: `py -m venv .venv && .venv\\Scripts\\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `python app.py`
6. Open `http://127.0.0.1:5000` in your browser.

The SQLite database (`vestra.db`) is created automatically on first run and starts with five sample clothing pieces. New uploaded images are stored as BLOBs in that database, so wardrobe data and photos can be backed up together by copying `vestra.db`. This keeps the local app self-contained; the tradeoff is that the database grows with each photo. Existing photos in `uploads/` continue to work.

## Main API routes
- `GET /api/items` — list wardrobe items
- `POST /api/items` — add an item (multipart form)
- `DELETE /api/items/<id>` — delete an item
- `GET /api/outfits` — list saved outfits
- `POST /api/outfits` — create an outfit (JSON)
- `DELETE /api/outfits/<id>` — delete an outfit
- `GET /api/stats` — dashboard counts

This is a local educational prototype. It does not yet include accounts, authentication, cloud hosting, or production security hardening. Flask debug mode is for local development only.
