#!/usr/bin/env python3
"""
Setup script to create test data for the AI assistant demo
"""
from app import app, db, User, Resource
from werkzeug.security import generate_password_hash

def create_test_data():
    with app.app_context():
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                pw_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            print("✓ Created admin user (admin/admin123)")

        # Create sample resources
        sample_resources = [
            {
                'name': 'Casa Tineretului Timișoara',
                'type': 'Space',
                'city': 'Timișoara',
                'lat': 45.7494,
                'lon': 21.2272,
                'capacity': 150,
                'description': 'Modern youth center with conference halls and event spaces',
                'contact': 'contact@casatineretului.ro',
                'url': 'https://casatineretului.ro',
                'category': 'Conference Hall'
            },
            {
                'name': 'LSAC Timișoara',
                'type': 'Volunteer',
                'city': 'Timișoara',
                'lat': 45.7489,
                'lon': 21.2087,
                'capacity': None,
                'description': 'Law Students Association organizing events and providing volunteers',
                'contact': 'lsac.timisoara@gmail.com',
                'url': 'https://lsac.ro',
                'category': 'Student Organization'
            },
            {
                'name': 'Politehnica University Timișoara',
                'type': 'Partner',
                'city': 'Timișoara',
                'lat': 45.7472,
                'lon': 21.2280,
                'capacity': 500,
                'description': 'Technical university open for academic partnerships and venue hosting',
                'contact': 'rectorat@upt.ro',
                'url': 'https://upt.ro',
                'category': 'University'
            },
            {
                'name': 'TechHub Timișoara',
                'type': 'Space',
                'city': 'Timișoara',
                'lat': 45.7536,
                'lon': 21.2251,
                'capacity': 80,
                'description': 'Co-working space and tech community hub with event facilities',
                'contact': 'hello@techhub.ro',
                'url': 'https://techhub.ro',
                'category': 'Tech Hub'
            },
            {
                'name': 'ADR Vest',
                'type': 'Grant',
                'city': 'Timișoara',
                'lat': 45.7501,
                'lon': 21.2300,
                'capacity': None,
                'description': 'Regional development agency providing EU funding for events and projects',
                'contact': 'office@adrvest.ro',
                'url': 'https://adrvest.ro',
                'category': 'Funding Agency'
            },
            {
                'name': 'Organizare Evenimente Pro',
                'type': 'Logistics',
                'city': 'Timișoara',
                'lat': 45.7520,
                'lon': 21.2290,
                'capacity': None,
                'description': 'Professional event management and catering services',
                'contact': '+40721234567',
                'url': 'https://evenimente-pro.ro',
                'category': 'Event Services'
            },
            {
                'name': 'DevTalks Conference',
                'type': 'Event',
                'city': 'Timișoara',
                'lat': 45.7450,
                'lon': 21.2320,
                'capacity': 300,
                'description': 'Annual tech conference - opportunity for networking and partnerships',
                'contact': 'info@devtalks.ro',
                'url': 'https://devtalks.ro',
                'category': 'Tech Conference'
            },
            {
                'name': 'Volunteers for Community',
                'type': 'Volunteer',
                'city': 'Timișoara',
                'lat': 45.7510,
                'lon': 21.2200,
                'capacity': None,
                'description': 'NGO coordinating volunteers for community events and social causes',
                'contact': 'volunteers@community.ro',
                'url': 'https://volunteers-community.ro',
                'category': 'NGO'
            }
        ]

        for resource_data in sample_resources:
            # Check if resource already exists
            existing = Resource.query.filter_by(name=resource_data['name']).first()
            if not existing:
                resource = Resource(**resource_data)
                db.session.add(resource)
                print(f"✓ Added resource: {resource_data['name']}")

        db.session.commit()
        print(f"\n🎉 Test data setup complete!")
        print(f"📍 Total resources in database: {Resource.query.count()}")
        print(f"👤 Admin user: admin/admin123")

if __name__ == '__main__':
    create_test_data()
