#!/usr/bin/env python3
"""
Security Monitoring and Update Automation
Monitors for security vulnerabilities and automates updates
"""

import json
import subprocess
import sys
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services.logging.elk_logger import LoggerFactory, ELKLogger
    USE_ELK = True
except ImportError:
    USE_ELK = False
    logging.basicConfig(level=logging.INFO)


class SecurityMonitor:
    """Monitors and manages security updates"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.setup_logging()
        self.vulnerabilities = []
        self.updates_applied = []
    
    def setup_logging(self):
        """Setup logging with optional ELK integration"""
        if USE_ELK and self.config.get('elk', {}).get('enabled', False):
            LoggerFactory.configure(
                logstash_host=self.config['elk'].get('host', 'localhost'),
                logstash_port=self.config['elk'].get('port', 5000)
            )
            self.elk_logger = LoggerFactory.get_elk_logger('SecurityMonitor')
            self.logger = self.elk_logger.get_logger()
        else:
            self.logger = logging.getLogger('SecurityMonitor')
            self.elk_logger = None
    
    def log_security_event(self, event: str, details: Dict[str, Any], level: str = "INFO"):
        """Log security event"""
        if self.elk_logger:
            self.elk_logger.log_security_event(event, details)
        else:
            self.logger.log(getattr(logging, level), f"{event}: {json.dumps(details)}")
    
    def check_system_updates(self) -> List[Dict[str, Any]]:
        """Check for system security updates"""
        self.logger.info("Checking system security updates...")
        updates = []
        
        try:
            # Update package lists
            subprocess.run(['apt-get', 'update', '-qq'], check=True, capture_output=True)
            
            # Check for security updates
            result = subprocess.run(
                ['apt-get', '-s', 'upgrade'],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if 'security' in line.lower() and 'inst' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        updates.append({
                            'package': parts[1],
                            'type': 'system',
                            'severity': 'high' if 'critical' in line.lower() else 'medium'
                        })
            
            self.log_security_event('system_updates_check', {
                'updates_found': len(updates),
                'packages': [u['package'] for u in updates]
            })
            
        except Exception as e:
            self.logger.error(f"Failed to check system updates: {e}")
            self.log_security_event('system_updates_error', {'error': str(e)}, 'ERROR')
        
        return updates
    
    def scan_docker_images(self) -> List[Dict[str, Any]]:
        """Scan Docker images for vulnerabilities"""
        self.logger.info("Scanning Docker images...")
        vulnerabilities = []
        
        try:
            # Get list of images
            result = subprocess.run(
                ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
                capture_output=True,
                text=True
            )
            
            images = [img.strip() for img in result.stdout.split('\n') if img.strip()]
            
            for image in images:
                if image.startswith('<none>') or image == 'scratch:latest':
                    continue
                
                self.logger.info(f"Scanning {image}...")
                
                # Scan with Trivy
                scan_result = subprocess.run(
                    ['trivy', 'image', '--format', 'json', '--security-checks', 'vuln', image],
                    capture_output=True,
                    text=True
                )
                
                if scan_result.returncode == 0:
                    try:
                        data = json.loads(scan_result.stdout)
                        for result in data.get('Results', []):
                            for vuln in result.get('Vulnerabilities', []):
                                if vuln.get('Severity') in ['CRITICAL', 'HIGH']:
                                    vulnerabilities.append({
                                        'image': image,
                                        'cve': vuln.get('VulnerabilityID'),
                                        'package': vuln.get('PkgName'),
                                        'severity': vuln.get('Severity'),
                                        'fixed_version': vuln.get('FixedVersion', 'none')
                                    })
                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to parse Trivy output for {image}")
            
            self.log_security_event('docker_scan_complete', {
                'images_scanned': len(images),
                'vulnerabilities_found': len(vulnerabilities),
                'critical': sum(1 for v in vulnerabilities if v['severity'] == 'CRITICAL'),
                'high': sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
            })
            
        except Exception as e:
            self.logger.error(f"Failed to scan Docker images: {e}")
            self.log_security_event('docker_scan_error', {'error': str(e)}, 'ERROR')
        
        return vulnerabilities
    
    def scan_python_packages(self) -> List[Dict[str, Any]]:
        """Scan Python packages for vulnerabilities"""
        self.logger.info("Scanning Python packages...")
        vulnerabilities = []
        
        try:
            # Run pip-audit
            result = subprocess.run(
                ['pip-audit', '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for vuln in data:
                    vulnerabilities.append({
                        'package': vuln.get('name'),
                        'version': vuln.get('version'),
                        'vulnerability': vuln.get('vulnerability_id'),
                        'description': vuln.get('description'),
                        'fixed_version': vuln.get('fixed_version')
                    })
            
            self.log_security_event('python_scan_complete', {
                'vulnerabilities_found': len(vulnerabilities),
                'packages': [v['package'] for v in vulnerabilities]
            })
            
        except Exception as e:
            self.logger.error(f"Failed to scan Python packages: {e}")
            self.log_security_event('python_scan_error', {'error': str(e)}, 'ERROR')
        
        return vulnerabilities
    
    def apply_updates(self, updates: List[Dict[str, Any]]) -> bool:
        """Apply security updates"""
        self.logger.info(f"Applying {len(updates)} updates...")
        success_count = 0
        
        for update in updates:
            try:
                if update['type'] == 'system':
                    # Apply system update
                    result = subprocess.run(
                        ['apt-get', 'install', '-y', '--only-upgrade', update['package']],
                        capture_output=True
                    )
                    if result.returncode == 0:
                        success_count += 1
                        self.updates_applied.append(update)
                        self.log_security_event('update_applied', update)
                
                elif update['type'] == 'python':
                    # Update Python package
                    result = subprocess.run(
                        ['pip', 'install', '--upgrade', f"{update['package']}>={update['fixed_version']}"],
                        capture_output=True
                    )
                    if result.returncode == 0:
                        success_count += 1
                        self.updates_applied.append(update)
                        self.log_security_event('update_applied', update)
                
            except Exception as e:
                self.logger.error(f"Failed to apply update {update}: {e}")
                self.log_security_event('update_failed', {'update': update, 'error': str(e)}, 'ERROR')
        
        self.logger.info(f"Successfully applied {success_count}/{len(updates)} updates")
        return success_count == len(updates)
    
    def send_notification(self, subject: str, message: str, priority: str = "INFO"):
        """Send notification about security events"""
        # Send to webhook if configured
        webhook_url = self.config.get('notifications', {}).get('webhook_url')
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'text': f"MT4 Security Alert - {subject}",
                    'attachments': [{
                        'color': 'danger' if priority == 'CRITICAL' else 'warning',
                        'text': message,
                        'ts': int(time.time())
                    }]
                })
            except Exception as e:
                self.logger.error(f"Failed to send webhook notification: {e}")
        
        # Log notification
        self.log_security_event('notification_sent', {
            'subject': subject,
            'priority': priority,
            'message': message
        })
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate security report"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'vulnerabilities': {
                'total': len(self.vulnerabilities),
                'critical': sum(1 for v in self.vulnerabilities if v.get('severity') == 'CRITICAL'),
                'high': sum(1 for v in self.vulnerabilities if v.get('severity') == 'HIGH'),
                'details': self.vulnerabilities
            },
            'updates_applied': {
                'total': len(self.updates_applied),
                'details': self.updates_applied
            },
            'scan_summary': {
                'docker_images': len(set(v['image'] for v in self.vulnerabilities if 'image' in v)),
                'python_packages': len(set(v['package'] for v in self.vulnerabilities if 'package' in v and 'image' not in v))
            }
        }
        
        # Save report
        report_path = Path(self.config.get('report_path', '/app/logs/security-report.json'))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_security_event('report_generated', {
            'path': str(report_path),
            'vulnerabilities': report['vulnerabilities']['total'],
            'updates_applied': report['updates_applied']['total']
        })
        
        return report
    
    def run(self):
        """Run security monitoring and updates"""
        self.logger.info("Starting security monitoring...")
        
        try:
            # 1. Check system updates
            system_updates = self.check_system_updates()
            
            # 2. Scan Docker images
            docker_vulns = self.scan_docker_images()
            self.vulnerabilities.extend(docker_vulns)
            
            # 3. Scan Python packages
            python_vulns = self.scan_python_packages()
            self.vulnerabilities.extend(python_vulns)
            
            # 4. Apply critical updates if auto-update is enabled
            if self.config.get('auto_update', {}).get('enabled', False):
                critical_updates = [
                    u for u in system_updates
                    if u.get('severity') == 'critical'
                ]
                if critical_updates:
                    self.logger.warning(f"Applying {len(critical_updates)} critical updates...")
                    self.apply_updates(critical_updates)
            
            # 5. Generate report
            report = self.generate_report()
            
            # 6. Send notifications for critical issues
            if report['vulnerabilities']['critical'] > 0:
                self.send_notification(
                    'Critical Vulnerabilities Found',
                    f"Found {report['vulnerabilities']['critical']} critical vulnerabilities",
                    'CRITICAL'
                )
            
            self.logger.info("Security monitoring completed")
            
        except Exception as e:
            self.logger.error(f"Security monitoring failed: {e}")
            self.log_security_event('monitoring_failed', {'error': str(e)}, 'ERROR')
            raise


def main():
    """Main entry point"""
    # Load configuration
    config_path = os.environ.get('SECURITY_CONFIG', '/app/config/security.json')
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        # Default configuration
        config = {
            'elk': {
                'enabled': True,
                'host': 'logstash',
                'port': 5000
            },
            'auto_update': {
                'enabled': False,
                'critical_only': True
            },
            'notifications': {
                'webhook_url': os.environ.get('SLACK_WEBHOOK_URL')
            },
            'report_path': '/app/logs/security-report.json'
        }
    
    # Run monitor
    monitor = SecurityMonitor(config)
    monitor.run()


if __name__ == '__main__':
    main()