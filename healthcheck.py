#!/usr/bin/env python3
import urllib.request
import sys

try:
    urllib.request.urlopen("http://localhost:8000/api/health")
except Exception:
    sys.exit(1)
