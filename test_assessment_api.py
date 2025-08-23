#!/usr/bin/env python3
"""
Simple test script to check assessment API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_assessment_detail():
    """Test getting assessment details"""
    assessment_id = "test-assessment-detailed"
    url = f"{BASE_URL}/assessments/{assessment_id}"
    
    print(f"Testing: GET {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_assessment_list():
    """Test getting assessment list"""
    url = f"{BASE_URL}/assessments/list"
    
    print(f"Testing: GET {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing Assessment API endpoints...")
    print("=" * 50)
    
    test_assessment_list()
    print("\n" + "=" * 50)
    test_assessment_detail()
