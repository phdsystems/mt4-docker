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
    """Test DLL libraries"""
    
    def test_dll_libraries_exist(self):
        """Test that required DLL files exist"""
        dll_files = [
            "MQL4/Libraries/libzmq.dll",
            "MQL4/Libraries/libsodium.dll"
        ]
        
        for dll_file in dll_files:
            path = self.project_root / dll_file
            self.assertTrue(path.exists(), f"{dll_file} not found")


class TestPythonComponents(TestMT4DockerBase):
    """Test Python components"""
    
    def test_imports(self):
        """Test that all Python modules can be imported"""
        modules_to_test = [
            "services.logging.elk_logger",
        ]
        
        for module in modules_to_test:
            try:
                __import__(module)
            except ImportError as e:
                self.fail(f"Failed to import {module}: {e}")
    
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
            "MQL4/Experts/StreamingPlatform_test.ex4",
            "MQL4/Include/phd-quants/integration/zmq/Zmq.mqh",
        ]
        
        for ea_file in ea_files:
            path = self.project_root / ea_file
            self.assertTrue(path.exists(), f"{ea_file} not found")
    
    def test_phd_quants_integration(self):
        """Test phd-quants integration files"""
        integration_files = [
            "MQL4/Include/phd-quants/integration/zmq/Context.mqh",
            "MQL4/Include/phd-quants/integration/zmq/Socket.mqh",
            "MQL4/Include/phd-quants/integration/zmq/Zmq.mqh",
        ]
        
        for file_path in integration_files:
            path = self.project_root / file_path
            self.assertTrue(path.exists(), f"{file_path} not found")


class TestAutomationScripts(TestMT4DockerBase):
    """Test automation scripts"""
    
    def test_start_script_exists(self):
        """Test that start script exists and is executable"""
        start_script = self.project_root / "infra/scripts/deploy/start.sh"
        self.assertTrue(start_script.exists(), "Start script not found")
        self.assertTrue(os.access(start_script, os.X_OK), "Start script not executable")
    
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
    
    def test_zmq_port_configuration(self):
        """Test that ZMQ port 32770 is configured"""
        # Check if running container exposes port 32770
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Ports}}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            # Check if any container has port 32770 mapped
            ports_output = result.stdout.strip()
            if "32770" in ports_output:
                self.assertIn("32770->32770/tcp", ports_output, 
                             "Port 32770 should be mapped for ZMQ streaming")
        
        # Also check docker-compose config for port mapping
        compose_file = self.project_root / "infra/docker/docker-compose.yml"
        if compose_file.exists():
            with open(compose_file, 'r') as f:
                content = f.read()
                # Check if port 32770 is mentioned in compose file
                if "32770" in content:
                    self.assertIn("32770:32770", content,
                                 "Port 32770 should be mapped in docker-compose.yml")


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