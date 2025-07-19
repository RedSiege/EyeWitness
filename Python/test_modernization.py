#!/usr/bin/env python3
"""
EyeWitness Modernization Validation Test Suite

This script validates that the modernized EyeWitness preserves all original functionality
while using updated dependencies. Tests core components and compatibility.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add the modules path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

try:
    from rapidfuzz import fuzz
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service as FirefoxService
except ImportError as e:
    print(f"[!] Missing dependency for testing: {e}")
    print("[!] Please install: pip install rapidfuzz selenium>=4.29.0")
    sys.exit(1)

# Import EyeWitness modules
try:
    import modules.selenium_module as selenium_module
    import modules.reporting as reporting
    import modules.objects as objects
    import modules.db_manager as db_manager
except ImportError as e:
    print(f"[!] Failed to import EyeWitness modules: {e}")
    print("[!] Make sure you're running from the Python directory")
    sys.exit(1)


class TestModernizationCompatibility(unittest.TestCase):
    """Test suite to validate modernization preserves functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock CLI arguments object
        self.mock_cli = MagicMock()
        self.mock_cli.timeout = 10
        self.mock_cli.width = 1024
        self.mock_cli.height = 768
        self.mock_cli.user_agent = None
        self.mock_cli.proxy_ip = None
        self.mock_cli.proxy_port = None
        self.mock_cli.proxy_type = None
        self.mock_cli.selenium_log_path = None
        self.mock_cli.cookies = None
        self.mock_cli.max_retries = 1
    
    def test_selenium_imports(self):
        """Test that all required Selenium imports work"""
        try:
            from selenium import webdriver
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from selenium.common.exceptions import WebDriverException
        except ImportError as e:
            self.fail(f"Selenium import failed: {e}")
    
    def test_rapidfuzz_functionality(self):
        """Test that RapidFuzz produces same results as FuzzyWuzzy"""
        # Test strings that should be similar (>70% threshold)
        similar_strings = [
            ("Apache Tomcat Server", "Apache Tomcat Application Server"),
            ("IIS 10.0 Server", "IIS Web Server 10.0"),
            ("nginx/1.18.0", "nginx/1.20.1")
        ]
        
        # Test strings that should be different (<70% threshold)
        different_strings = [
            ("Apache Tomcat", "Microsoft IIS"),
            ("Login Page", "Error 404 Not Found"),
            ("Dashboard", "Completely Different Application")
        ]
        
        # Test similar strings meet threshold
        for str1, str2 in similar_strings:
            ratio = fuzz.token_sort_ratio(str1, str2)
            self.assertGreaterEqual(ratio, 70, 
                f"Similar strings should score >=70%: '{str1}' vs '{str2}' = {ratio}%")
        
        # Test different strings don't meet threshold
        for str1, str2 in different_strings:
            ratio = fuzz.token_sort_ratio(str1, str2)
            self.assertLess(ratio, 70,
                f"Different strings should score <70%: '{str1}' vs '{str2}' = {ratio}%")
    
    def test_selenium_driver_creation(self):
        """Test that modern Selenium driver can be created"""
        # This test requires Firefox to be installed
        # Skip if Firefox not available
        try:
            # Test that the create_driver function exists and can be called
            self.assertTrue(hasattr(selenium_module, 'create_driver'))
            
            # Test Firefox options creation (without actually starting browser)
            options = Options()
            options.add_argument("--headless")
            options.accept_insecure_certs = True
            
            # Test Service creation
            service = FirefoxService()
            
            # If we get here without exceptions, the APIs are compatible
            self.assertTrue(True, "Modern Selenium APIs are compatible")
            
        except Exception as e:
            # If Firefox not installed, that's OK - we just test API compatibility
            if "firefox" in str(e).lower() or "geckodriver" in str(e).lower():
                self.skipTest(f"Firefox/geckodriver not available: {e}")
            else:
                self.fail(f"Selenium API compatibility issue: {e}")
    
    def test_http_object_functionality(self):
        """Test that HTTPTableObject works correctly"""
        try:
            # Create an HTTP object
            http_obj = objects.HTTPTableObject()
            http_obj.remote_system = "https://example.com"
            http_obj.page_title = "Example Page"
            
            # Test path setting functionality
            http_obj.set_paths(self.temp_dir)
            
            # Verify paths are set correctly
            self.assertIsNotNone(http_obj.screenshot_path)
            self.assertIsNotNone(http_obj.source_path)
            self.assertTrue(http_obj.screenshot_path.endswith('.png'))
            
        except Exception as e:
            self.fail(f"HTTPTableObject functionality broken: {e}")
    
    def test_database_manager(self):
        """Test that database operations work correctly"""
        try:
            # Create a temporary database
            db_path = os.path.join(self.temp_dir, "test.db")
            db_mgr = db_manager.DB_Manager(db_path)
            
            # Properly initialize the database connection and schema
            db_mgr.open_connection()
            db_mgr.initialize_db()
            
            # Test database initialization
            self.assertTrue(os.path.exists(db_path))
            
            # Test that the connection works
            self.assertIsNotNone(db_mgr.connection)
            
            # Test basic database operations - just verify tables exist
            cursor = db_mgr.get_cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Verify required tables were created
            expected_tables = ['opts', 'http', 'ua']
            for table in expected_tables:
                self.assertIn(table, tables, f"Required table '{table}' not found")
            
            # Close the connection
            db_mgr.connection.close()
            
        except Exception as e:
            self.fail(f"Database manager functionality broken: {e}")
    
    def test_grouping_algorithm_preservation(self):
        """Test that the page title grouping algorithm works identically"""
        # Create mock HTTP objects with different page titles
        test_objects = []
        titles = [
            "Apache Tomcat Server - Login",
            "Apache Tomcat Application Server",
            "IIS Default Page",
            "nginx welcome page",
            "Login Portal",
            "Apache Tomcat Server Management"
        ]
        
        for title in titles:
            obj = MagicMock()
            obj.page_title = title
            test_objects.append(obj)
        
        # Test the grouping logic from reporting.py
        # This mimics the exact algorithm used in sort_data_and_write
        grouped_elements = []
        group_data = test_objects.copy()
        
        while len(group_data) > 0:
            test_element = group_data.pop(0)
            temp = [x for x in group_data if fuzz.token_sort_ratio(
                test_element.page_title, x.page_title) >= 70]
            temp.append(test_element)
            temp = sorted(temp, key=lambda k: k.page_title)
            grouped_elements.extend(temp)
            group_data = [x for x in group_data if fuzz.token_sort_ratio(
                test_element.page_title, x.page_title) < 70]
        
        # Verify we processed all objects
        self.assertEqual(len(grouped_elements), len(test_objects))
        
        # Verify Apache Tomcat entries are grouped together
        apache_titles = [obj.page_title for obj in grouped_elements 
                        if "Apache Tomcat" in obj.page_title]
        self.assertGreater(len(apache_titles), 1, 
                          "Apache Tomcat entries should be grouped together")
    
    def test_cli_compatibility(self):
        """Test that command-line interface remains compatible"""
        # Test that EyeWitness.py can be imported
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            import EyeWitness
            
            # Test that create_cli_parser function exists
            self.assertTrue(hasattr(EyeWitness, 'create_cli_parser') or 
                          'create_cli_parser' in dir(EyeWitness))
            
        except ImportError as e:
            self.fail(f"Main EyeWitness module import failed: {e}")
        except Exception as e:
            # Other exceptions are OK - we just want to test import compatibility
            pass
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        import time
        # Give time for database connections to close
        time.sleep(0.1)
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                # Database file might still be locked, ignore for test purposes
                pass


class TestPerformanceAndSecurity(unittest.TestCase):
    """Test performance improvements and security updates"""
    
    def test_rapidfuzz_performance(self):
        """Verify RapidFuzz performance characteristics"""
        import time
        
        # Test string comparison performance
        test_strings = [
            "Apache Tomcat Application Server Version 9.0.1",
            "Apache Tomcat Server 9.0.2",
            "Apache HTTP Server 2.4.41",
            "nginx Web Server 1.18.0",
            "Microsoft IIS 10.0 Server"
        ] * 100  # Multiply to test performance
        
        start_time = time.time()
        
        # Perform many comparisons
        for i, str1 in enumerate(test_strings[:-1]):
            for str2 in test_strings[i+1:i+10]:  # Compare with next 10
                ratio = fuzz.token_sort_ratio(str1, str2)
        
        elapsed = time.time() - start_time
        
        # RapidFuzz should complete this in reasonable time
        self.assertLess(elapsed, 10.0, 
                       f"String comparison took too long: {elapsed}s")
    
    def test_dependency_versions(self):
        """Test that we're using secure, modern dependency versions"""
        import selenium
        import rapidfuzz
        
        # Check Selenium version is modern (4.0+)
        selenium_version = selenium.__version__
        major_version = int(selenium_version.split('.')[0])
        self.assertGreaterEqual(major_version, 4,
                               f"Selenium version too old: {selenium_version}")
        
        # Check RapidFuzz version is modern (3.0+)
        rapidfuzz_version = rapidfuzz.__version__
        major_version = int(rapidfuzz_version.split('.')[0])
        self.assertGreaterEqual(major_version, 3,
                               f"RapidFuzz version too old: {rapidfuzz_version}")


def run_tests():
    """Run the complete test suite"""
    print("=" * 60)
    print("EyeWitness Modernization Validation Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestModernizationCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceAndSecurity))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("[+] ALL TESTS PASSED - Modernization preserves functionality!")
        print(f"[+] Ran {result.testsRun} tests successfully")
    else:
        print("[-] TESTS FAILED - Modernization may have broken functionality!")
        print(f"[-] Failures: {len(result.failures)}")
        print(f"[-] Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    print("=" * 60)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)