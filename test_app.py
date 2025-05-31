#!/usr/bin/env python3
"""
Test script to verify the AI chatbot functionality
"""
import json
from app import app

def test_chat_api():
    with app.test_client() as client:
        # Test the chat API endpoint
        test_message = "I need a venue for 100 people in Timișoara for a hackathon"

        response = client.post('/api/chat',
                              json={'message': test_message},
                              content_type='application/json')

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_json()}")

def test_resources_api():
    with app.test_client() as client:
        # Test the resources API endpoint
        response = client.get('/api/resources')
        data = response.get_json()

        print(f"\nResources API Status: {response.status_code}")
        print(f"Number of resources: {len(data) if data else 0}")
        if data:
            print("Sample resource:")
            print(json.dumps(data[0], indent=2))

if __name__ == '__main__':
    print("🧪 Testing AI Chatbot Application")
    print("=" * 40)

    # Test basic functionality first
    test_resources_api()

    # Test chat functionality (will fail if no OpenAI API key)
    print("\n🤖 Testing Chat API (requires OPENAI_API_KEY):")
    test_chat_api()
