#!/usr/bin/env python3
"""
Manual Test Script for Slack Worker
====================================
Run this to test ROTA reminders locally without waiting for scheduled time.

Usage:
    python test_manual.py              # Test everything
    python test_manual.py --summary    # Test summary only
    python test_manual.py --dm          # Test DMs only
"""

import sys
import os
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from slack_bolt import App
from slack_worker.jobs.rota_reminder_job import RotaReminderJob
from slack_worker.utils.lock_manager import LockManager

def main():
    parser = argparse.ArgumentParser(description='Test ROTA reminders manually')
    parser.add_argument('--summary', action='store_true', help='Test summary posting only')
    parser.add_argument('--dm', action='store_true', help='Test DM reminders only')
    parser.add_argument('--period', default='This Week', help='Time period (This Week or Next Week)')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🧪 MANUAL TEST - ROTA Reminder Job")
    print("="*70)
    
    # Check configuration
    test_channel = os.getenv("ROTA_GROUP_CHANNEL", "")
    if not test_channel:
        print("\n❌ Error: ROTA_GROUP_CHANNEL not set in environment")
        print("   Set it in .env file or export ROTA_GROUP_CHANNEL=C123456789")
        sys.exit(1)
    
    print(f"\n📋 Test Configuration:")
    print(f"   Channel:  {test_channel}")
    print(f"   Period:   {args.period}")
    print(f"   Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Timezone: {os.getenv('TIMEZONE', 'UTC')}")
    print("-"*70)
    
    # Initialize
    try:
        slack_app = App(token=config.SLACK_BOT_TOKEN)
        lock_manager = LockManager(lock_dir=os.getenv("LOCK_DIR", "/tmp/slack_worker_locks"))
        
        # Verify bot can connect
        auth = slack_app.client.auth_test()
        print(f"\n✅ Bot connected: @{auth['user']}")
        
        # Create job
        job = RotaReminderJob(
            slack_app=slack_app,
            lock_manager=lock_manager
        )
        
        # Override channel for testing
        job.group_channel = test_channel
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        print("\nPossible issues:")
        print("   - SLACK_BOT_TOKEN not set or invalid")
        print("   - Bot not installed to workspace")
        print("   - Network/connection issue")
        sys.exit(1)
    
    # Run tests based on arguments
    success_count = 0
    total_tests = 0
    
    if args.summary or (not args.summary and not args.dm):
        total_tests += 1
        print(f"\n{'='*70}")
        print(f"📊 Test 1: Post Summary to Channel")
        print(f"{'='*70}")
        print(f"   Period: {args.period}")
        print(f"   Channel: {test_channel}")
        try:
            job._post_rota_summary(args.period)
            print(f"   ✅ SUCCESS - Check your Slack channel!")
            success_count += 1
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    if args.dm or (not args.summary and not args.dm):
        total_tests += 1
        print(f"\n{'='*70}")
        print(f"💬 Test 2: Send DM Reminders")
        print(f"{'='*70}")
        print(f"   Period: {args.period}")
        try:
            job._dm_rota_participants(args.period)
            print(f"   ✅ SUCCESS - Check your Slack DMs!")
            success_count += 1
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    # Test history update (optional)
    if not args.summary and not args.dm:
        total_tests += 1
        print(f"\n{'='*70}")
        print(f"📝 Test 3: Update History Sheet")
        print(f"{'='*70}")
        try:
            job._update_history_sheet(args.period)
            print(f"   ✅ SUCCESS - History sheet updated (if implemented)")
            success_count += 1
        except Exception as e:
            print(f"   ⚠️  SKIPPED or FAILED: {e}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 Test Results: {success_count}/{total_tests} passed")
    print(f"{'='*70}")
    
    if success_count == total_tests:
        print(f"\n🎉 All tests passed!")
        print(f"   ✓ Check your test channel: {test_channel}")
        print(f"   ✓ Check DMs for assigned users")
    else:
        print(f"\n⚠️  Some tests failed. Check logs above for details.")
    
    print()

if __name__ == "__main__":
    main()

