#!/usr/bin/env python3
"""
Simple test script for the Genetic Disorder Detection API
"""

import requests
import json
import os
from typing import Dict, Any

class GeneticAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None

    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/")
            print(f"Health check: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
                return True
            return False
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

    def test_detailed_health(self) -> bool:
        """Test the detailed health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            print(f"Detailed health check: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"Health status: {health_data['status']}")
                for component, status in health_data['components'].items():
                    print(f"  {component}: {status}")
                return health_data['status'] == 'healthy'
            return False
        except Exception as e:
            print(f"Detailed health check failed: {e}")
            return False

    def test_register(self, email: str, password: str) -> bool:
        """Test user registration"""
        try:
            data = {"email": email, "password": password}
            response = self.session.post(f"{self.base_url}/auth/register", json=data)
            print(f"Register: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Registration successful: {result.get('message')}")
                return True
            elif response.status_code == 400:
                print(f"Registration failed (expected): {response.json()}")
                return True  # User might already exist
            return False
        except Exception as e:
            print(f"Registration failed: {e}")
            return False

    def test_login(self, email: str, password: str) -> bool:
        """Test user login"""
        try:
            data = {"username": email, "password": password}
            response = self.session.post(f"{self.base_url}/auth/login", data=data)
            print(f"Login: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                self.token = result.get('access_token')
                print(f"Login successful, token received")
                return True
            return False
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def test_chat_with_text(self, message: str) -> bool:
        """Test chat endpoint with text message"""
        if not self.token:
            print("No token available, skipping chat test")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"message": message}
            response = self.session.post(f"{self.base_url}/chat", data=data, headers=headers)
            print(f"Chat with text: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Chat successful, session_id: {result.get('session_id')}")
                print(f"Response: {result.get('response')[:100]}...")
                return True
            return False
        except Exception as e:
            print(f"Chat with text failed: {e}")
            return False

    def test_chat_with_file(self, file_path: str) -> bool:
        """Test chat endpoint with VCF file"""
        if not self.token:
            print("No token available, skipping file upload test")
            return False

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with open(file_path, 'rb') as f:
                files = {"file": f}
                response = self.session.post(f"{self.base_url}/chat", files=files, headers=headers)
            print(f"Chat with file: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"File upload successful, session_id: {result.get('session_id')}")
                print(f"Response: {result.get('response')[:100]}...")
                return True
            return False
        except Exception as e:
            print(f"Chat with file failed: {e}")
            return False

    def test_get_chats(self) -> bool:
        """Test getting chat history"""
        if not self.token:
            print("No token available, skipping get chats test")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{self.base_url}/chats", headers=headers)
            print(f"Get chats: {response.status_code}")
            if response.status_code == 200:
                chats = response.json()
                print(f"Found {len(chats)} chats")
                return True
            return False
        except Exception as e:
            print(f"Get chats failed: {e}")
            return False

    def run_all_tests(self, email: str = "test@example.com", password: str = "testpassword123"):
        """Run all tests"""
        print("=" * 50)
        print("Running Genetic API Tests")
        print("=" * 50)

        tests = [
            ("Health Check", lambda: self.test_health_check()),
            ("Detailed Health", lambda: self.test_detailed_health()),
            ("Register", lambda: self.test_register(email, password)),
            ("Login", lambda: self.test_login(email, password)),
            ("Get Chats", lambda: self.test_get_chats()),
            ("Chat with Text", lambda: self.test_chat_with_text("What is BRCA1?")),
        ]

        # Add file upload test if sample file exists
        sample_file = "uploads/sample_with_genotypes.vcf"
        if os.path.exists(sample_file):
            tests.append(("Chat with File", lambda: self.test_chat_with_file(sample_file)))

        results = []
        for test_name, test_func in tests:
            print(f"\n--- Testing {test_name} ---")
            try:
                result = test_func()
                results.append((test_name, result))
                print(f"{test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                print(f"{test_name}: ERROR - {e}")
                results.append((test_name, False))

        print("\n" + "=" * 50)
        print("Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        return passed == total

if __name__ == "__main__":
    tester = GeneticAPITester()
    success = tester.run_all_tests()
    exit(0 if success else 1) 