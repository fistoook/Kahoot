#!/usr/bin/env python3
"""Quick test to see the welcome message"""

import socket
import time

sock = socket.socket()
sock.connect(('127.0.0.1', 5555))

print("=== WELCOME MESSAGE TEST ===\n")

# Receive welcome message
sock.settimeout(2)
try:
    data = sock.recv(4096)
    print("Received from server:")
    print(data.decode(errors='ignore'))
except socket.timeout:
    print("Timeout waiting for message")

sock.close()
