# public_resources_map/import_csv.py
"""
One-time bulk loader.
Duplicate lines (same name + coords) are ignored.
"""
import csv
from pathlib import Path

from app import app, db, Place

CSV_FILE = Path(__file__).with_name("resources.csv")

def import_csv():
    with app.app_context():
        with open(CSV_FILE, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                exists = Place.query.filter_by(
                    name=row["name"],
                    lat=float(row["lat"]),
                    lon=float(row["lon"])
                ).first()
                if not exists:
                    db.session.add(Place(
                        name=row["name"],
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                        type=row["type"],
                        capacity=int(row["capacity"] or 0)
                    ))
        db.session.commit()
        print("CSV import finished.")

if __name__ == "__main__":
    import_csv()
