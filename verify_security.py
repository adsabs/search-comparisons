#!/usr/bin/env python3
"""
Security verification script to check for hardcoded credentials.
"""

import os
import re
import sys
from pathlib import Path

# Patterns to search for
DANGEROUS_PATTERNS = [
    # Common credential patterns
    r'password\s*=\s*["\'][^"\']{8,}["\']',
    r'api_key\s*=\s*["\'][A-Za-z0-9]{20,}["\']',
    r'secret\s*=\s*["\'][^"\']{8,}["\']',
    r'token\s*=\s*["\'][A-Za-z0-9]{20,}["\']',
    
    # Specific known secrets (now removed)
    r'F6pHGICMXXy4aiAWBR4gaFL4Ta72xdM8jVhHDOsm',
    r'c707e3d691c5f681f31a05b4c68bb09fc402597f325213a2e6411beebf199405',
    r'\$kw7Thr&nUNBZ!',
    
    # Bearer tokens
    r'Bearer\s+[A-Za-z0-9]{30,}',
    
    # Basic auth patterns (base64 encoded)
    r'Basic\s+[A-Za-z0-9+/=]{20,}',
]

def scan_file(filepath):
    """Scan a file for dangerous patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        issues = []
        for i, line in enumerate(content.split('\n'), 1):
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip comments and documentation examples
                    stripped = line.strip()
                    if not (stripped.startswith('#') or 
                           stripped.startswith('//') or
                           'example' in stripped.lower() or
                           'placeholder' in stripped.lower() or
                           'your_' in stripped.lower() or
                           'REDACTED' in stripped):
                        issues.append(f"Line {i}: {line.strip()}")
        
        return issues
    except Exception as e:
        print(f"Error scanning {filepath}: {e}")
        return []

def main():
    """Main security verification function."""
    print("🔒 Security Verification: Checking for hardcoded credentials...")
    
    # Directories to scan
    scan_dirs = [
        'backend/app',
        'backend/tests',
        'backend/scripts',
    ]
    
    total_issues = 0
    
    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
            
        print(f"\n📁 Scanning {scan_dir}...")
        
        for py_file in Path(scan_dir).rglob('*.py'):
            # Skip certain files
            if any(skip in str(py_file) for skip in ['__pycache__', '.pyc', 'verify_security.py']):
                continue
                
            issues = scan_file(py_file)
            if issues:
                print(f"\n⚠️  SECURITY ISSUE in {py_file}:")
                for issue in issues:
                    print(f"   {issue}")
                total_issues += len(issues)
    
    print(f"\n📊 Security Scan Summary:")
    print(f"   Total issues found: {total_issues}")
    
    if total_issues == 0:
        print("✅ No hardcoded credentials found! All security checks passed.")
        return 0
    else:
        print("❌ Security issues detected! Please review and fix the above issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
