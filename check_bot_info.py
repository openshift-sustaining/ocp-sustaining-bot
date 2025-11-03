#!/usr/bin/env python
"""
Check Bot Information
=====================
Run this to find your bot's exact name and verify it's working.
"""

from config import config
from slack_bolt import App

print("\n" + "="*60)
print("🤖 Checking Bot Information...")
print("="*60 + "\n")

try:
    # Initialize app
    app = App(token=config.SLACK_BOT_TOKEN)
    
    # Get bot info
    auth_response = app.client.auth_test()
    
    print("✅ Bot is configured and can connect to Slack!\n")
    print("📋 Bot Details:")
    print(f"   Bot Name:    @{auth_response.get('user', 'N/A')}")
    print(f"   Bot ID:      {auth_response.get('user_id', 'N/A')}")
    print(f"   Team:        {auth_response.get('team', 'N/A')}")
    print(f"   Team ID:     {auth_response.get('team_id', 'N/A')}")
    
    bot_id = auth_response['user_id']
    
    # Get more detailed bot info
    try:
        bot_info = app.client.users_info(user=bot_id)
        user_data = bot_info['user']
        
        print(f"\n👤 Full Bot Profile:")
        print(f"   Display Name: {user_data.get('profile', {}).get('display_name', 'N/A')}")
        print(f"   Real Name:    {user_data.get('real_name', 'N/A')}")
        print(f"   Status:       {'🟢 Active' if user_data.get('deleted') == False else '🔴 Inactive'}")
        
        print(f"\n💡 To invite this bot to a channel, use:")
        print(f"   /invite @{auth_response.get('user', 'bot-name')}")
        
    except Exception as e:
        print(f"\n⚠️  Could not get detailed bot info: {e}")
    
    # List channels the bot is already in
    print(f"\n📢 Channels bot is currently in:")
    try:
        channels = app.client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=True
        )
        
        bot_channels = []
        for channel in channels.get('channels', []):
            try:
                members = app.client.conversations_members(channel=channel['id'])
                if bot_id in members.get('members', []):
                    bot_channels.append(f"   - #{channel['name']} (ID: {channel['id']})")
            except:
                pass  # Skip channels we can't access
        
        if bot_channels:
            print('\n'.join(bot_channels))
        else:
            print("   ⚠️  Bot is not in any channels yet!")
            print("   💡 Use /invite @bot-name in a channel to add it")
    
    except Exception as e:
        print(f"   ⚠️  Could not list channels : {e}")
    
    print("\n" + "="*60)
    print("✅ Check complete!")
    print("="*60 + "\n")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPossible issues:")
    print("1. SLACK_BOT_TOKEN not set or invalid")
    print("2. Bot not installed to workspace")
    print("3. Network/connection issue")
    print("\n💡 Fix:")
    print("   - Check your .env file has SLACK_BOT_TOKEN=xoxb-...")
    print("   - Go to api.slack.com/apps and reinstall the app")
    print("   - Make sure you're using the Bot User OAuth Token")

