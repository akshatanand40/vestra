# VESTRA — Smart Digital Wardrobe

A beginner-friendly Flask + MongoDB wardrobe project.

## Features
- View and search wardrobe items
- Filter by clothing category
- Add clothing items with optional image uploads
- Delete wardrobe items
- Create outfits from saved wardrobe pieces
- View and delete saved outfits
- Dashboard counts powered by the database

## Database and photo storage

Wardrobe items, outfits, and uploaded photo bytes are saved in MongoDB. Photos are stored as binary data in each item's document. The upload limit is 5 MB per photo; MongoDB documents support up to 16 MiB, and Atlas Free clusters have 512 MB total storage. The free cluster is suitable for this small demo, but monitor its storage as photos accumulate.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment (recommended):
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows: `py -m venv .venv && .venv\\Scripts\\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a MongoDB Atlas database and set `MONGODB_URI` to its connection string. Keep the URI private; do not commit it to GitHub.
6. Start the app: `python app.py`
7. Open `http://127.0.0.1:5000` in your browser.

For the hosted app, add `MONGODB_URI` as an environment variable in Render. Do not paste the connection string into source files or commit it. The app adds five sample clothing pieces when the MongoDB `items` collection is empty. Existing rows in the local `vestra.db` are not copied automatically; upload any photos you want to keep again through the app.

## Main API routes
- `GET /api/items` — list wardrobe items
- `POST /api/items` — add an item (multipart form)
- `DELETE /api/items/<id>` — delete an item
- `GET /api/outfits` — list saved outfits
- `POST /api/outfits` — create an outfit (JSON)
- `DELETE /api/outfits/<id>` — delete an outfit
- `GET /api/stats` — dashboard counts

This is an educational demo. It does not yet include accounts or authentication, so all visitors share the same wardrobe. Flask debug mode is for local development only.
