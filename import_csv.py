# public_resources_map/import_csv.py
"""
Bulk-import for timis_public_resources.csv
Usage:
    python import_csv.py path/to/timis_public_resources.csv
If path is omitted, defaults to ./timis_public_resources.csv
Duplicates (same name + lat + lon) are skipped.
"""
import csv, sys, pathlib
from app import app, db, Place

csv_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "timis_public_resources.csv")
if not csv_path.exists():
    print(f"CSV not found: {csv_path}")
    sys.exit(1)

with app.app_context():
    added = skipped = 0
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name, lat, lon = row["Name"], float(row["Lat"]), float(row["Lon"])
            exists = Place.query.filter_by(name=name, lat=lat, lon=lon).first()
            if exists:
                skipped += 1
                continue
            place = Place(
                name=name,
                type=row["Category"],
                lat=lat, lon=lon,
                city=row.get("City") or None,
                url=row.get("URL") or None,
                category=row.get("Category") or None
            )
            db.session.add(place)
            added += 1
        db.session.commit()
    print(f"Imported: {added}  |  Skipped duplicates: {skipped}")
