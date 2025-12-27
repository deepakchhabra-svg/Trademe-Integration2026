#!/usr/bin/env python3
"""
Health Check Script for Retail OS
Verifies all system components are functioning correctly
"""

import sys
import os
import sqlite3
import requests
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

class HealthChecker:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'overall_status': 'HEALTHY'
        }
        
    def check_database(self):
        """Check database connectivity and integrity"""
        print("[*] Checking database...")
        try:
            db_path = PROJECT_ROOT / 'trademe_store.db'
            if not db_path.exists():
                self.results['checks']['database'] = {
                    'status': 'FAIL',
                    'message': 'Database file not found'
                }
                self.results['overall_status'] = 'UNHEALTHY'
                print("  [X] Database file not found")
                return
            
            # Check database size
            db_size = db_path.stat().st_size / (1024 * 1024)  # MB
            
            # Check connectivity
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = [
                'suppliers', 'supplier_products', 'internal_products',
                'trademe_listings', 'system_commands'
            ]
            
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                self.results['checks']['database'] = {
                    'status': 'WARN',
                    'message': f'Missing tables: {", ".join(missing_tables)}',
                    'size_mb': round(db_size, 2)
                }
                print(f"  [!] Missing tables: {', '.join(missing_tables)}")
            else:
                # Get row counts
                counts = {}
                for table in required_tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                
                self.results['checks']['database'] = {
                    'status': 'PASS',
                    'message': 'Database healthy',
                    'size_mb': round(db_size, 2),
                    'tables': counts
                }
                print(f"  [OK] Database healthy ({round(db_size, 2)} MB)")
                for table, count in counts.items():
                    print(f"     - {table}: {count} rows")
            
            conn.close()
            
        except Exception as e:
            self.results['checks']['database'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            self.results['overall_status'] = 'UNHEALTHY'
            print(f"  [X] Database check failed: {e}")
    
    def check_environment(self):
        """Check environment configuration"""
        print("\n[*] Checking environment configuration...")
        try:
            env_path = PROJECT_ROOT / '.env'
            if not env_path.exists():
                self.results['checks']['environment'] = {
                    'status': 'WARN',
                    'message': '.env file not found'
                }
                print("  [!] .env file not found")
                return
            
            # Check required variables
            required_vars = [
                'CONSUMER_KEY', 'CONSUMER_SECRET',
                'ACCESS_TOKEN', 'ACCESS_TOKEN_SECRET'
            ]
            
            with open(env_path) as f:
                env_content = f.read()
            
            missing_vars = [var for var in required_vars if var not in env_content]
            
            if missing_vars:
                self.results['checks']['environment'] = {
                    'status': 'FAIL',
                    'message': f'Missing variables: {", ".join(missing_vars)}'
                }
                self.results['overall_status'] = 'UNHEALTHY'
                print(f"  [X] Missing variables: {', '.join(missing_vars)}")
            else:
                self.results['checks']['environment'] = {
                    'status': 'PASS',
                    'message': 'All required variables present'
                }
                print("  [OK] Environment configuration complete")
                
        except Exception as e:
            self.results['checks']['environment'] = {
                'status': 'FAIL',
                'message': str(e)
            }
            self.results['overall_status'] = 'UNHEALTHY'
            print(f"  [X] Environment check failed: {e}")
    
    def check_dashboard(self):
        """Check if dashboard is accessible"""
        print("\n[*] Checking dashboard...")
        try:
            response = requests.get('http://localhost:8501/_stcore/health', timeout=5)
            if response.status_code == 200:
                self.results['checks']['dashboard'] = {
                    'status': 'PASS',
                    'message': 'Dashboard is running'
                }
                print("  [OK] Dashboard is running (http://localhost:8501)")
            else:
                self.results['checks']['dashboard'] = {
                    'status': 'FAIL',
                    'message': f'Dashboard returned status {response.status_code}'
                }
                print(f"  [X] Dashboard returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.results['checks']['dashboard'] = {
                'status': 'WARN',
                'message': 'Dashboard not running (connection refused)'
            }
            print("  [!] Dashboard not running")
        except Exception as e:
            self.results['checks']['dashboard'] = {
                'status': 'WARN',
                'message': str(e)
            }
            print(f"  [!] Dashboard check failed: {e}")
    
    def check_media_directory(self):
        """Check media directory"""
        print("\n[*] Checking media directory...")
        try:
            media_path = PROJECT_ROOT / 'data' / 'media'
            if not media_path.exists():
                self.results['checks']['media'] = {
                    'status': 'WARN',
                    'message': 'Media directory not found'
                }
                print("  [!] Media directory not found")
                return
            
            # Count files and calculate size
            files = list(media_path.rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            total_size = sum(f.stat().st_size for f in files if f.is_file()) / (1024 * 1024)  # MB
            
            self.results['checks']['media'] = {
                'status': 'PASS',
                'message': 'Media directory accessible',
                'file_count': file_count,
                'size_mb': round(total_size, 2)
            }
            print(f"  [OK] Media directory: {file_count} files ({round(total_size, 2)} MB)")
            
        except Exception as e:
            self.results['checks']['media'] = {
                'status': 'WARN',
                'message': str(e)
            }
            print(f"  [!] Media check failed: {e}")
    
    def check_recent_activity(self):
        """Check for recent scraping activity"""
        print("\n[*] Checking recent activity...")
        try:
            db_path = PROJECT_ROOT / 'trademe_store.db'
            if not db_path.exists():
                print("  [!] Cannot check activity (database not found)")
                return
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check for products added in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM supplier_products 
                WHERE created_at > datetime('now', '-1 day')
            """)
            recent_products = cursor.fetchone()[0]
            
            # Check for listings created in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM trademe_listings 
                WHERE created_at > datetime('now', '-1 day')
            """)
            recent_listings = cursor.fetchone()[0]
            
            if recent_products > 0 or recent_listings > 0:
                self.results['checks']['activity'] = {
                    'status': 'PASS',
                    'message': 'Recent activity detected',
                    'products_24h': recent_products,
                    'listings_24h': recent_listings
                }
                print(f"  [OK] Recent activity: {recent_products} products, {recent_listings} listings (24h)")
            else:
                self.results['checks']['activity'] = {
                    'status': 'WARN',
                    'message': 'No activity in last 24 hours',
                    'products_24h': 0,
                    'listings_24h': 0
                }
                print("  [!] No activity in last 24 hours")
            
            conn.close()
            
        except Exception as e:
            self.results['checks']['activity'] = {
                'status': 'WARN',
                'message': str(e)
            }
            print(f"  [!] Activity check failed: {e}")
    
    def check_logs(self):
        """Check for recent errors in logs"""
        print("\n[*] Checking logs...")
        try:
            log_path = PROJECT_ROOT / 'production_sync.log'
            if not log_path.exists():
                self.results['checks']['logs'] = {
                    'status': 'WARN',
                    'message': 'Log file not found'
                }
                print("  [!] Log file not found")
                return
            
            # Read last 1000 lines
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-1000:]
            
            # Count errors
            error_count = sum(1 for line in lines if 'ERROR' in line or 'FAILED' in line)
            
            if error_count > 10:
                self.results['checks']['logs'] = {
                    'status': 'WARN',
                    'message': f'{error_count} errors found in recent logs',
                    'error_count': error_count
                }
                print(f"  [!] {error_count} errors found in recent logs")
            else:
                self.results['checks']['logs'] = {
                    'status': 'PASS',
                    'message': f'{error_count} errors in recent logs',
                    'error_count': error_count
                }
                print(f"  [OK] Logs healthy ({error_count} errors)")
                
        except Exception as e:
            self.results['checks']['logs'] = {
                'status': 'WARN',
                'message': str(e)
            }
            print(f"  [!] Log check failed: {e}")
    
    def run_all_checks(self):
        """Run all health checks"""
        print("=" * 60)
        print("RETAIL OS HEALTH CHECK")
        print("=" * 60)
        
        self.check_database()
        self.check_environment()
        self.check_dashboard()
        self.check_media_directory()
        self.check_recent_activity()
        self.check_logs()
        
        print("\n" + "=" * 60)
        print(f"OVERALL STATUS: {self.results['overall_status']}")
        print("=" * 60)
        
        # Save results to file
        results_path = PROJECT_ROOT / 'health_check_results.json'
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {results_path}")
        
        # Return exit code
        return 0 if self.results['overall_status'] == 'HEALTHY' else 1

if __name__ == '__main__':
    checker = HealthChecker()
    exit_code = checker.run_all_checks()
    sys.exit(exit_code)
