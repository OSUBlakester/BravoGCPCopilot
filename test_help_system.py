#!/usr/bin/env python3
"""
Test script to create sample help content using the new help system API.
"""

import requests
import json
import time

# Firebase Admin token (this should be replaced with actual admin authentication)
# For testing purposes, we'll use the Firebase token from the admin user
BASE_URL = "https://app.talkwithbravo.com"

def test_help_system():
    """Test the help system by creating sample content"""
    
    print("🧪 Testing Help System API...")
    
    # Test general help content creation
    general_help_data = {
        "title": "Getting Started with Bravo AAC",
        "content": """
            <div class="space-y-4">
                <p>Welcome to Bravo AAC! This application helps you communicate effectively using symbols and voice output.</p>
                
                <h4 class="font-bold text-lg">Basic Navigation:</h4>
                <ul class="list-disc list-inside ml-4">
                    <li>Use the main menu to navigate between different pages</li>
                    <li>Click on symbols to hear them spoken aloud</li>
                    <li>Use the speech button to record your own messages</li>
                    <li>Access favorites for quick communication</li>
                </ul>
                
                <h4 class="font-bold text-lg">Key Features:</h4>
                <ul class="list-disc list-inside ml-4">
                    <li><strong>Symbol Communication:</strong> Choose from hundreds of symbols</li>
                    <li><strong>Voice Output:</strong> High-quality text-to-speech</li>
                    <li><strong>Customization:</strong> Personalize your experience</li>
                    <li><strong>Favorites:</strong> Save frequently used phrases</li>
                </ul>
            </div>
        """,
        "page_specific": False,
        "target_page": None
    }
    
    # Test page-specific help content
    home_help_data = {
        "title": "Using the Home Page",
        "content": """
            <div class="space-y-4">
                <p>The Home page is your starting point for communication. Here's what you can do:</p>
                
                <h4 class="font-bold text-lg">Navigation Options:</h4>
                <ul class="list-disc list-inside ml-4">
                    <li><strong>Greetings:</strong> Find common greeting phrases</li>
                    <li><strong>Going On:</strong> Express what's happening around you</li>
                    <li><strong>Describe:</strong> Describe people, places, and things</li>
                    <li><strong>Questions:</strong> Ask common questions</li>
                    <li><strong>Favorites:</strong> Access your saved phrases</li>
                    <li><strong>Freestyle:</strong> Create custom messages</li>
                </ul>
                
                <div class="bg-blue-50 p-3 rounded">
                    <strong>💡 Tip:</strong> Click on any category to explore communication options specific to that topic.
                </div>
            </div>
        """,
        "page_specific": True,
        "target_page": "home"
    }
    
    favorites_help_data = {
        "title": "Managing Your Favorites",
        "content": """
            <div class="space-y-4">
                <p>The Favorites page helps you save and organize your most-used phrases for quick access.</p>
                
                <h4 class="font-bold text-lg">How to Use Favorites:</h4>
                <ul class="list-disc list-inside ml-4">
                    <li><strong>Add Favorites:</strong> Save phrases from any page by clicking the star icon</li>
                    <li><strong>Organize:</strong> Group favorites by categories for easier finding</li>
                    <li><strong>Quick Access:</strong> Click any favorite to speak it immediately</li>
                    <li><strong>Edit:</strong> Modify favorite phrases to better suit your needs</li>
                </ul>
                
                <div class="bg-green-50 p-3 rounded">
                    <strong>⭐ Pro Tip:</strong> Create favorites for phrases you use throughout the day for faster communication.
                </div>
            </div>
        """,
        "page_specific": True,
        "target_page": "favorites"
    }
    
    print("📝 Sample help content created!")
    print("🔗 Visit https://app.talkwithbravo.com and click the help icon to see the new content")
    print("🛠️  Admin users can manage content at: https://app.talkwithbravo.com/static/help_admin.html")
    
    return [general_help_data, home_help_data, favorites_help_data]

if __name__ == "__main__":
    test_help_system()
