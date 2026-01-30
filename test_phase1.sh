#!/bin/bash
# Phase 1 Testing Script
# Tests chat history metadata classification

echo "=========================================="
echo "Phase 1: Chat History Metadata Testing"
echo "=========================================="
echo ""

# Test 1: Check latest chat messages
echo "✅ Test 1: Checking latest chat messages with metadata..."
python3 check_chat_metadata.py

echo ""
echo "=========================================="
echo "Manual Testing Instructions:"
echo "=========================================="
echo ""
echo "1. Generate and select DIFFERENT message types:"
echo "   - Greetings (Hello, Hi, etc.)"
echo "   - Jokes (click Jokes button)"
echo "   - Questions (click Questions button if available)"
echo "   - Statements (click other buttons)"
echo ""
echo "2. Test REPETITION detection:"
echo "   - Select the SAME joke/greeting 2-3 times"
echo "   - Should be marked as repetition after first time"
echo ""
echo "3. Verify UI shows AI-Extracted Narrative section:"
echo "   - Go to: http://localhost:8000/static/user_info_admin.html"
echo "   - Look for purple-bordered 'AI-Extracted Narrative' section"
echo "   - Should show 'No narrative extracted yet' (expected)"
echo ""
echo "4. After creating varied messages, run this script again"
echo "   to see the metadata classifications"
echo ""
echo "=========================================="
