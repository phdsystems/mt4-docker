#!/usr/bin/env python3
"""
Comprehensive Test Suite for MT4 Docker ZeroMQ
Runs unit tests, integration tests, and end-to-end tests
"""

import unittest
import sys
import os
import subprocess
import time
import json
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMT4DockerBase(unittest.TestCase):
    """Base test class with common utilities"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.project_root = Path(__file__).parent.parent
        cls.temp_dir = tempfile.mkdtemp()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)


class TestDLLBuild(TestMT4DockerBase):
    """Test DLL compilation and functionality"""
    
    def test_dll_source_exists(self):
        """Test that DLL source files exist"""
        dll_source = self.project_root / "dll_source" / "mt4zmq_winsock_fixed.cpp"
        self.assertTrue(dll_source.exists(), "DLL source file not found")
    
    def test_dll_can_compile(self):
        """Test that DLL can be compiled"""
        # Check if MinGW is installed
        result = subprocess.run(["which", "i686-w64-mingw32-g++"], capture_output=True)
        if result.returncode != 0:
            self.skipTest("MinGW not installed")
        
        # Test compilation command
        dll_dir = self.project_root / "dll_source"
        compile_cmd = [
            "i686-w64-mingw32-g++",
            "-shared",
            "-o", str(self.temp_dir) + "/test_mt4zmq.dll",
            str(dll_dir / "mt4zmq_winsock_fixed.cpp"),
            "-lws2_32", "-static-libgcc", "-static-libstdc++",
            "-Wl,--kill-at", "-Wl,--enable-stdcall-fixup",
            "-DUNICODE", "-D_UNICODE"
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"DLL compilation failed: {result.stderr}")
        
        # Check DLL was created
        dll_file = Path(self.temp_dir) / "test_mt4zmq.dll"
        self.assertTrue(dll_file.exists(), "DLL file not created")
        self.assertGreater(dll_file.stat().st_size, 100000, "DLL file too small")


class TestPythonComponents(TestMT4DockerBase):
    """Test Python components"""
    
    def test_imports(self):
        """Test that all Python modules can be imported"""
        modules_to_test = [
            "services.logging.elk_logger",
            "services.security.zmq_secure",
            "services.zeromq_bridge.zmq_bridge_oop",
        ]
        
        for module in modules_to_test:
            try:
                __import__(module)
            except ImportError as e:
                self.fail(f"Failed to import {module}: {e}")
    
    def test_security_key_generation(self):
        """Test security key generation"""
        from services.security.zmq_secure import KeyManager
        
        km = KeyManager(self.temp_dir)
        
        # Generate server keys
        server_keys = km.generate_server_keys("test_server")
        self.assertTrue(Path(server_keys['public']).exists())
        self.assertTrue(Path(server_keys['secret']).exists())
        
        # Generate client keys
        client_keys = km.generate_client_keys("test_client")
        self.assertTrue(Path(client_keys['public']).exists())
        self.assertTrue(Path(client_keys['secret']).exists())
        self.assertTrue(Path(client_keys['authorized']).exists())
    
    def test_elk_logger(self):
        """Test ELK logger functionality"""
        from services.logging.elk_logger import LoggerFactory, ELKLogger
        
        # Configure logger
        LoggerFactory.configure(
            logstash_host='localhost',
            logstash_port=5000,
            console_output=False
        )
        
        # Get logger
        logger = LoggerFactory.get_elk_logger('test')
        self.assertIsInstance(logger, ELKLogger)
        
        # Test logging methods
        logger.log_market_tick('EURUSD', 1.1000, 1.1001, 100)
        logger.log_security_event('test_event', {'key': 'value'})
        logger.log_performance_metric('test_metric', 42.0)


class TestDockerConfiguration(TestMT4DockerBase):
    """Test Docker configurations"""
    
    def test_dockerfile_exists(self):
        """Test that Dockerfiles exist"""
        dockerfiles = [
            "infra/docker/Dockerfile",
            "infra/docker/Dockerfile.python",
            "infra/docker/Dockerfile.security-updater"
        ]
        
        for dockerfile in dockerfiles:
            path = self.project_root / dockerfile
            self.assertTrue(path.exists(), f"{dockerfile} not found")
    
    def test_docker_compose_files(self):
        """Test Docker Compose files"""
        compose_files = [
            "infra/docker/docker-compose.yml",
            "infra/docker/docker-compose.elk.yml",
            "infra/docker/docker-compose.secure.yml",
            "infra/docker/docker-compose.security.yml"
        ]
        
        for compose_file in compose_files:
            path = self.project_root / compose_file
            if path.exists():
                # Validate YAML syntax
                import yaml
                with open(path, 'r') as f:
                    try:
                        yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        self.fail(f"Invalid YAML in {compose_file}: {e}")
    
    def test_docker_compose_config(self):
        """Test docker-compose configuration"""
        result = subprocess.run(
            ["docker", "compose", "-f", "infra/docker/docker-compose.yml", "config"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Parse the configuration
            import yaml
            config = yaml.safe_load(result.stdout)
            
            # Check required services
            self.assertIn('services', config)
            self.assertIn('mt4', config['services'])


class TestMQL4Files(TestMT4DockerBase):
    """Test MQL4 files"""
    
    def test_expert_advisors_exist(self):
        """Test that EA files exist"""
        ea_files = [
            "MQL4/Experts/MT4ZMQBridge.mq4",
            "MQL4/Include/MT4ZMQ.mqh",
            "MQL4/Scripts/TestZMQDLLIntegration.mq4"
        ]
        
        for ea_file in ea_files:
            path = self.project_root / ea_file
            self.assertTrue(path.exists(), f"{ea_file} not found")
    
    def test_mql4_syntax(self):
        """Basic syntax check for MQL4 files"""
        mql4_file = self.project_root / "MQL4/Experts/MT4ZMQBridge.mq4"
        
        with open(mql4_file, 'r') as f:
            content = f.read()
            
            # Check for required elements
            self.assertIn("#property copyright", content)
            self.assertIn("#import \"mt4zmq.dll\"", content)
            self.assertIn("OnInit()", content)
            self.assertIn("OnDeinit(", content)
            self.assertIn("OnTimer()", content)


class TestAutomationScripts(TestMT4DockerBase):
    """Test automation scripts"""
    
    def test_setup_script_exists(self):
        """Test that setup script exists and is executable"""
        setup_script = self.project_root / "infra/scripts/setup/setup_mt4_zmq.sh"
        self.assertTrue(setup_script.exists(), "Setup script not found")
        self.assertTrue(os.access(setup_script, os.X_OK), "Setup script not executable")
    
    def test_makefile_exists(self):
        """Test that Makefile exists"""
        makefile = self.project_root / "Makefile"
        self.assertTrue(makefile.exists(), "Makefile not found")
    
    def test_makefile_targets(self):
        """Test Makefile targets"""
        result = subprocess.run(
            ["make", "-n", "help"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Check for key targets
            targets = ["setup", "build", "deploy", "test", "clean"]
            for target in targets:
                self.assertIn(target, output)


class TestZeroMQIntegration(TestMT4DockerBase):
    """Test ZeroMQ integration"""
    
    def test_zmq_imports(self):
        """Test ZeroMQ Python imports"""
        try:
            import zmq
            self.assertIsNotNone(zmq.zmq_version())
        except ImportError:
            self.skipTest("PyZMQ not installed")
    
    def test_basic_pub_sub(self):
        """Test basic ZeroMQ pub/sub functionality"""
        try:
            import zmq
        except ImportError:
            self.skipTest("PyZMQ not installed")
        
        context = zmq.Context()
        
        # Create publisher
        publisher = context.socket(zmq.PUB)
        publisher.bind("tcp://127.0.0.1:15555")
        
        # Create subscriber
        subscriber = context.socket(zmq.SUB)
        subscriber.connect("tcp://127.0.0.1:15555")
        subscriber.subscribe(b"test")
        
        # Allow time for connection
        time.sleep(0.1)
        
        # Send message
        publisher.send_multipart([b"test", b"hello"])
        
        # Receive message
        subscriber.setsockopt(zmq.RCVTIMEO, 1000)
        try:
            topic, msg = subscriber.recv_multipart()
            self.assertEqual(topic, b"test")
            self.assertEqual(msg, b"hello")
        except zmq.Again:
            self.fail("No message received")
        finally:
            publisher.close()
            subscriber.close()
            context.term()


class TestEndToEnd(TestMT4DockerBase):
    """End-to-end integration tests"""
    
    def test_docker_services_config(self):
        """Test that all services can be configured"""
        # This would normally test actual service startup
        # For CI, we just validate configurations
        
        services_to_check = [
            ("docker", ["docker", "version"]),
            ("docker compose", ["docker", "compose", "version"]),
            ("python3", ["python3", "--version"]),
        ]
        
        for service_name, cmd in services_to_check:
            result = subprocess.run(cmd, capture_output=True)
            self.assertEqual(
                result.returncode, 0,
                f"{service_name} not available or not working"
            )
    
    def test_requirements_file(self):
        """Test that requirements.txt is valid"""
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Basic format check
                        self.assertTrue(
                            '==' in line or '>=' in line or '~=' in line,
                            f"Invalid requirement format: {line}"
                        )


def run_test_suite():
    """Run the complete test suite"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDLLBuild,
        TestPythonComponents,
        TestDockerConfiguration,
        TestMQL4Files,
        TestAutomationScripts,
        TestZeroMQIntegration,
        TestEndToEnd
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)