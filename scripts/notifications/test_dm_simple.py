#!/usr/bin/env python3
"""
Simple DM test - send a direct message to a user
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from slack_worker.slack_client import slack_client

# Your user ID
USER_ID = "U09PYDCDA7R"

# Simple test message
message = """
:robot_face: *Test DM from Bot*
Let me know if you received this! :wave:
"""

print("\n" + "=" * 80)
print("SLACK DM TEST")
print("=" * 80)
print(f"\n Sending test DM to user: {USER_ID}")
print("\n Message Preview:")
print("-" * 80)
print(message)
print("-" * 80)

try:
    print("\n⏳ Sending...")
    success = slack_client.send_dm(user_id=USER_ID, text=message)

    if success:
        print("SUCCESS! DM sent to you!")
    else:
        print("FAILED - Message was not sent")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 80)
