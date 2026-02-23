#!/bin/bash

# Guess Who Game - Local Testing Diagnostic Script
# This script checks if all components are properly set up before local testing

echo "================================================"
echo "Guess Who Game - Setup Diagnostic"
echo "================================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

WORKSPACE="/Users/blakethomas/Documents/BravoGCPCopilot"
PASSED=0
FAILED=0
WARNINGS=0

# Check 1: Workspace exists
echo -n "1. Workspace directory exists... "
if [ -d "$WORKSPACE" ]; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 2: server.py exists
echo -n "2. server.py exists... "
if [ -f "$WORKSPACE/server.py" ]; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 3: guess_who.html exists
echo -n "3. guess_who.html exists... "
if [ -f "$WORKSPACE/static/guess_who.html" ]; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 4: guess_who.js exists
echo -n "4. guess_who.js exists... "
if [ -f "$WORKSPACE/static/guess_who.js" ]; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 5: gridpage.js exists
echo -n "5. gridpage.js exists... "
if [ -f "$WORKSPACE/static/gridpage.js" ]; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 6: Guess Who endpoints in server.py
echo -n "6. Guess Who endpoints in server.py... "
if grep -q "/api/guess-who/categories" "$WORKSPACE/server.py" && \
   grep -q "/api/guess-who/generate-people" "$WORKSPACE/server.py" && \
   grep -q "/api/guess-who/generate-clues" "$WORKSPACE/server.py"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 7: Guess Who integration in gridpage.js
echo -n "7. Guess Who navigation in gridpage.js... "
if grep -q "guess-who\|guesswho" "$WORKSPACE/static/gridpage.js"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (May need navigation integration)"
    ((WARNINGS++))
fi

# Check 8: authenticatedFetch function exists
echo -n "8. authenticatedFetch function in gridpage.js... "
if grep -q "function authenticatedFetch\|const authenticatedFetch" "$WORKSPACE/static/gridpage.js"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 9: announce function exists
echo -n "9. announce function in gridpage.js... "
if grep -q "function announce\|const announce" "$WORKSPACE/static/gridpage.js"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 10: startAuditoryScanning function exists
echo -n "10. startAuditoryScanning function in gridpage.js... "
if grep -q "startAuditoryScanning" "$WORKSPACE/static/gridpage.js"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 11: LLM endpoint in server.py
echo -n "11. /llm endpoint in server.py... "
if grep -q '/llm\|"/llm' "$WORKSPACE/server.py"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (LLM endpoint may not be available)"
    ((WARNINGS++))
fi

# Check 12: /play-audio endpoint in server.py
echo -n "12. /play-audio endpoint in server.py... "
if grep -q '/play-audio' "$WORKSPACE/server.py"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (Audio playback may not work)"
    ((WARNINGS++))
fi

# Check 13: config.py or environment setup
echo -n "13. config.py exists or environment ready... "
if [ -f "$WORKSPACE/config.py" ] || [ -f "$WORKSPACE/.env" ]; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (May need environment variables set)"
    ((WARNINGS++))
fi

# Check 14: Python environment (check if Python is available)
echo -n "14. Python 3 available... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✓${NC} ($PYTHON_VERSION)"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 15: FastAPI installed
echo -n "15. FastAPI installed... "
if python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (Will need to install: pip3 install fastapi uvicorn)"
    ((WARNINGS++))
fi

# Check 16: Firebase Admin SDK installed
echo -n "16. Firebase Admin SDK installed... "
if python3 -c "import firebase_admin" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (Will need to install: pip3 install firebase-admin)"
    ((WARNINGS++))
fi

# Check 17: Google AI (Gemini) SDK installed
echo -n "17. Google Generative AI SDK... "
if python3 -c "import google.generativeai" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (Will need to install: pip3 install google-generativeai)"
    ((WARNINGS++))
fi

# Check 18: HTML elements in guess_who.html
echo -n "18. All 6 game screens in HTML... "
SCREENS_FOUND=0
for screen in "category-screen" "mode-screen" "person-screen" "clue-screen" "guess-screen" "game-over-screen"; do
    if grep -q "id=\"$screen\"\|id='$screen'" "$WORKSPACE/static/guess_who.html"; then
        ((SCREENS_FOUND++))
    fi
done
if [ $SCREENS_FOUND -eq 6 ]; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} (Found $SCREENS_FOUND/6)"
    ((FAILED++))
fi

# Check 19: gridContainer class in HTML
echo -n "19. Grid containers in HTML... "
CONTAINERS=$(grep -c "class=\".*gridContainer\|class='.*gridContainer" "$WORKSPACE/static/guess_who.html")
if [ $CONTAINERS -gt 0 ]; then
    echo -e "${GREEN}✓${NC} ($CONTAINERS containers)"
    ((PASSED++))
else
    echo -e "${RED}✗${NC}"
    ((FAILED++))
fi

# Check 20: Scanning CSS in HTML
echo -n "20. Scanning highlight CSS... "
if grep -q "\.scanning\|outline.*#f97316\|outline.*orange" "$WORKSPACE/static/guess_who.html"; then
    echo -e "${GREEN}✓${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} (May not highlight buttons during scanning)"
    ((WARNINGS++))
fi

echo ""
echo "================================================"
echo "Summary:"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "================================================"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ Setup incomplete. Please fix failures above.${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Setup mostly complete but has warnings.${NC}"
    echo "Run: pip3 install fastapi uvicorn firebase-admin google-generativeai flask-cors"
    exit 0
else
    echo -e "${GREEN}✅ All checks passed! Ready for testing.${NC}"
    exit 0
fi
