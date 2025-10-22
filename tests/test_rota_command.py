#!/usr/bin/env python3
"""
Test ROTA command with mocked Google Sheets
============================================
Use this to test ROTA commands without real Google Sheets setup.
"""

from unittest.mock import Mock, patch
import sys

# Mock data matching your ROTA sheet
MOCK_DATA = {
    "This Week": [
        ["4.14.58", "10/20/2025", "10/24/2025", "German", "Amit", "Sanket C", "This Week"]
    ],
    "Next Week": [
        ["4.15.59", "2025-10-27", "2025-10-31", "Jaspreet", "Shiwani", "Aditya", "Next Week"]
    ],
    "4.14.58": ["4.14.58", "10/20/2025", "10/24/2025", "German", "Amit", "Sanket C", "This Week"]
}

def test_rota_check():
    """Test the rota --check command"""
    
    # Mock gsheet
    mock_gsheet = Mock()
    mock_gsheet.fetch_data_by_time = lambda period: MOCK_DATA.get(period, [])
    mock_gsheet.fetch_data_by_release = lambda release: MOCK_DATA.get(release)
    
    # Mock say function
    messages = []
    def mock_say(msg):
        messages.append(msg)
        print(f"\n📬 Bot says:\n{msg}\n")
    
    # Get a valid user ID
    test_user = "U123TEST"
    try:
        from config import config
        if hasattr(config, 'ROTA_USERS') and config.ROTA_USERS:
            test_user = list(config.ROTA_USERS.values())[0]
    except:
        pass
    
    # Patch gsheet
    with patch('slack_handlers.handlers.gsheet', mock_gsheet):
        from slack_handlers.handlers import handle_rota
        
        # Test 1: Check This Week
        print("="*70)
        print("Test 1: rota --check --time='This Week'")
        print("="*70)
        messages.clear()
        handle_rota(
            say=mock_say,
            user=test_user,
            params_dict={"check": True, "time": "This Week"}
        )
        
        # Test 2: Check specific release
        print("\n" + "="*70)
        print("Test 2: rota --check --release=4.14.58")
        print("="*70)
        messages.clear()
        handle_rota(
            say=mock_say,
            user=test_user,
            params_dict={"check": True, "release": "4.14.58"}
        )

if __name__ == "__main__":
    test_rota_check()

