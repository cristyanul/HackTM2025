"""
python create_user.py alice supersecret
"""
import sys
from werkzeug.security import generate_password_hash
from app import db, User, app

if len(sys.argv)!=3:
    print("Usage: python create_user.py <username> <password>")
    sys.exit(1)

username, pwd = sys.argv[1:3]
with app.app_context():
    if User.query.filter_by(username=username).first():
        print("User exists – updating password.")
        u = User.query.filter_by(username=username).first()
        u.pw_hash = generate_password_hash(pwd)
    else:
        u = User(username=username, pw_hash=generate_password_hash(pwd))
        db.session.add(u)
    db.session.commit()
    print("Done.")
