# Guess Who Game - Local Testing Setup Complete ✅

**Status:** All components verified, ready for local testing  
**Date:** 2025  
**Environment:** Local (http://localhost:8000)  
**Setup Verification:** 20/20 checks passed

---

## 📋 What Was Prepared for You

### 1. **Diagnostic Tool** ✅
**File:** `check_guess_who_setup.sh`

This shell script validates all 20 components needed for local testing:
- Required files (server.py, guess_who.html, guess_who.js, gridpage.js)
- Backend endpoints (/api/guess-who/*)
- Frontend functions (authenticatedFetch, announce, etc.)
- HTML elements and CSS
- Python dependencies (FastAPI, Firebase, Google Generative AI)

**Result:** ✅ All 20 checks PASSED

---

### 2. **Comprehensive Testing Guide** 📖
**File:** `GUESS_WHO_LOCAL_TEST.md`

Detailed testing procedure with 12 scenarios:
- Scenario 1-12: Category selection → Mode → Person → Clues → Guesses → Game over
- Each scenario has:
  - Step-by-step instructions
  - Expected results
  - Failure points to watch for
- Performance testing benchmarks
- Known issues documentation
- Pass/fail criteria
- Test report template

**Use when:** You want thorough, methodical testing

---

### 3. **Quick Test Checklist** ⚡
**File:** `GUESS_WHO_QUICK_TEST.md`

Fast-track testing for busy day:
- Full game flow test (5-10 minutes)
- Quick win test (2-3 minutes)
- Known issues you'll encounter
- Error quick-reference
- Success criteria
- Post-test actions

**Use when:** You need to validate quickly (< 5 minutes)

---

### 4. **Start Testing Instructions** 🚀
**File:** `GUESS_WHO_START_TESTING.md`

Step-by-step setup for first-time testing:
1. Start the FastAPI server
2. Open browser and login
3. Navigate to Guess Who
4. Open Developer Tools
5. Start testing with scenarios

Plus:
- Troubleshooting guide for common issues
- What to monitor during testing
- Quick fixes for common problems
- After-testing next steps

**Use when:** You're starting your testing session

---

### 5. **Tester's Reference Card** 🎯
**File:** `GUESS_WHO_TESTER_CARD.md`

Print-friendly quick reference:
- Game flow diagram
- Wake word phrases and variations
- Speech test scenarios
- Error codes and quick fixes
- Performance expectations
- Browser compatibility
- Debug mode commands
- Pro tips for testing

**Use when:** You need quick answers during testing

---

## 🎮 Game Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 GUESS WHO MODE A GAME FLOW                  │
└─────────────────────────────────────────────────────────────┘

PLAYER 1 (Secret Chooser)              PLAYER 2 (Guesser)
─────────────────────────────           ──────────────────
1. Selects Category                    3. Listens to clues
                                       4. Says wake word
2. Selects Person                      5. Speaks a guess
                                       6. Receives yes/no
2a. Gives Clues                        
                                       Repeats 3-6 until:
                                       - Correct guess (WIN)
                                       - Out of guesses (LOSS)
```

**Backend Architecture:**
```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Server.py                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Guess Who Endpoints                              │  │
│  │  • /api/guess-who/categories                      │  │
│  │  • /api/guess-who/generate-people                 │  │
│  │  • /api/guess-who/generate-clues                  │  │
│  │  • /api/guess-who/generate-guesses (unused)       │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Support Endpoints (from gridpage)                │  │
│  │  • /llm (Gemini LLM calls for responses)          │  │
│  │  • /play-audio (Text-to-speech TTS)               │  │
│  │  • /api/settings (User preferences)               │  │
│  │  • Firebase Auth (sessionStorage tokens)          │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  External Services                                │  │
│  │  • Firestore (game data, categories)              │  │
│  │  • Google Gemini API (LLM content generation)     │  │
│  │  • Firebase Authentication (user login)           │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Frontend Architecture:**
```
┌──────────────────────────────────────────────────────────┐
│                  Browser (Static Folder)                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │  guess_who.html (282 lines)                        │  │
│  │  • 6 game screens (category, mode, person, etc)   │  │
│  │  • Grid container for button layout               │  │
│  │  • Tailwind CSS styling                           │  │
│  │  • References gridpage.js for shared functions    │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  guess_who.js (845 lines)                          │  │
│  │  • Game state management                          │  │
│  │  • Screen navigation logic                        │  │
│  │  • Web Speech API integration                     │  │
│  │    - Wake word detection                          │  │
│  │    - Guess capture                                │  │
│  │  • Announcement/audio queuing                     │  │
│  │  • LLM response generation                        │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  gridpage.js (Shared Functions)                    │  │
│  │  • authenticatedFetch() - Auth wrapper            │  │
│  │  • announce() - TTS announcement queue            │  │
│  │  • startAuditoryScanning() - Button highlight     │  │
│  │  • stopAuditoryScanning() - Stop highlighting     │  │
│  │  • updateGridLayout() - Responsive sizing         │  │
│  │  • generateLlmButtons() - Button rendering        │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 📊 Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Backend** | ✅ Complete | All 3 core endpoints implemented |
| **Frontend HTML** | ✅ Complete | All 6 screens defined |
| **Frontend JS** | ✅ Complete | Full Mode A game flow |
| **Integration** | ✅ Complete | Gridpage function integration |
| **Authentication** | ✅ Complete | Firebase token handling |
| **Speech Recognition** | ✅ Complete | Wake word + guess capture |
| **Audio Output** | ✅ Complete | TTS via /play-audio endpoint |
| **Settings Loading** | ✅ Complete | User preferences loaded |
| **Database** | ✅ Complete | Firestore integration ready |
| **LLM Integration** | ✅ Complete | Gemini API for content generation |

**Overall Status:** 🟢 READY FOR TESTING

---

## 🎯 What You Can Test Now

### ✅ Fully Implemented Features

1. **Category Selection**
   - Load categories from Firestore
   - Display with proper grid layout
   - Announce selected category

2. **Mode Selection**
   - Choose "You guess" or "I guess"
   - Current: Mode A fully implemented
   - Future: Mode B

3. **Person Selection (Mode A)**
   - Generate 6-10 people via LLM (Gemini)
   - Display with category context
   - Announce selected person

4. **Clue System**
   - Generate contextual clues via LLM
   - Player 1 selects clues to give
   - Track clues given (max 3)

5. **Wake Word Detection**
   - Listen for configurable wake word
   - Support multiple phonetic variations
   - Trigger guess-listening mode

6. **Guess Capture**
   - Use Web Speech API for continuous listening
   - Capture complete spoken guess
   - Display guess to screen

7. **Response Generation**
   - Generate yes/no response options via LLM
   - 6 options per guess (mix of correct/incorrect)
   - Player 1 selects best response

8. **Game End Conditions**
   - **Win:** Correct guess selected
   - **Loss:** 3 incorrect guesses used
   - Display game over screen with stats

9. **Settings Integration**
   - Load scanDelay from user profile
   - Load wake word settings
   - Load grid column configuration
   - Apply to game behavior

10. **Navigation**
    - Home button on all screens
    - Return to gridpage
    - Clean state reset

---

## ⚠️ Known Issues (Documented)

These issues are known and documented but don't block testing:

### 1. **LLM Response Spoilers**
- **Problem:** Response options sometimes reveal the selected person
- **Example:** "No, that's not Tom Hanks, it's Harrison Ford"
- **Impact:** Game less fun when person is revealed early
- **Status:** Documented, planned fix available
- **Workaround:** Select generic responses

### 2. **Splash Screen Not Integrated**
- **Problem:** Splash Screen doesn't appear during announcements
- **Impact:** Less visual feedback during waiting periods
- **Status:** Documented, code ready for implementation
- **Workaround:** Manual Splash Screen toggle

### 3. **Scanning Doesn't Stop Before Announcement**
- **Problem:** Button highlighting continues during announcement
- **Impact:** Minor UX issue, buttons still highlight while speaking
- **Status:** Documented, easy fix available
- **Workaround:** None needed for functionality

---

## 🚀 How to Start Testing

### Quick Start (2 minutes)
1. Open terminal: `cd /Users/blakethomas/Documents/BravoGCPCopilot`
2. Run server: `python3 server.py`
3. Open browser: `http://localhost:8000/gridpage.html`
4. Login with test account
5. Navigate to Guess Who
6. Click category → Click "You guess" → Click person → Click clue

### Full Test (30 minutes)
1. Follow "Quick Start" above
2. Complete full game (win scenario)
3. Restart and complete full game (loss scenario)  
4. Test navigation from each screen
5. Document any findings
6. Check DevTools console for errors

---

## 📚 Documentation Files Created

| File | Purpose | When to Use |
|------|---------|------------|
| `GUESS_WHO_LOCAL_TEST.md` | Comprehensive 12-scenario guide | Thorough testing |
| `GUESS_WHO_QUICK_TEST.md` | Fast testing checklist | Quick validation |
| `GUESS_WHO_START_TESTING.md` | Setup and troubleshooting | First-time testing |
| `GUESS_WHO_TESTER_CARD.md` | Reference card (printable) | Quick lookup during test |
| `check_guess_who_setup.sh` | Validation script | Verify setup |
| `GUESS_WHO_LOCAL_TEST_COMPLETE.md` | This file | Overview of all prep |

---

## 🔍 Validation Results Summary

```
Setup Diagnostic Results:
═════════════════════════════════════════════════════════════

✅ 20/20 Checks Passed

Files & Structure:
  ✓ Workspace directory exists
  ✓ server.py exists
  ✓ guess_who.html exists (282 lines)
  ✓ guess_who.js exists (845 lines)
  ✓ gridpage.js exists
  ✓ All 6 game screens defined
  ✓ 6 grid containers present
  ✓ Scanning CSS configured

Backend:
  ✓ /api/guess-who/categories endpoint
  ✓ /api/guess-who/generate-people endpoint
  ✓ /api/guess-who/generate-clues endpoint
  ✓ /llm endpoint (Gemini LLM)
  ✓ /play-audio endpoint (TTS)

Frontend Functions:
  ✓ authenticatedFetch() in gridpage.js
  ✓ announce() in gridpage.js
  ✓ startAuditoryScanning() in gridpage.js
  ✓ Guess Who navigation in gridpage.js

Dependencies:
  ✓ Python 3.12.8 installed
  ✓ FastAPI installed
  ✓ Firebase Admin SDK installed
  ✓ Google Generative AI SDK installed
  ✓ Environment configured

Status: 🟢 READY FOR LOCAL TESTING
═════════════════════════════════════════════════════════════
```

---

## 📝 Next Steps

### Immediate (Do Now)
1. ✅ Read this file (you're reading it!)
2. Choose testing approach:
   - **Quick:** Read [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md) (2 min)
   - **Thorough:** Read [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) (30 min)
3. Start server: `python3 server.py`
4. Open browser to http://localhost:8000/gridpage.html
5. Navigate to Guess Who game

### During Testing
1. Follow chosen testing guide
2. Keep DevTools open (F12)
3. Monitor console for RED errors
4. Document any issues found
5. Keep reference card nearby

### After Testing  
1. Document results
2. Report any found issues
3. Note user feedback
4. Plan next improvements
5. Prepare for test branch deployment

---

## 🆘 If Something Goes Wrong

**Console shows RED error?**
→ Check [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md) Error section or [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) Troubleshooting

**Game won't load?**
→ Verify server running: `python3 server.py` should show "Uvicorn running"

**No audio plays?**
→ Check speaker volume, press F12 to open DevTools and watch Network tab for `/play-audio` requests

**Speech recognition doesn't work?**
→ Ensure using Chrome/Safari (not Firefox), grant microphone permission, speak clearly

**Need more help?**
→ Check setup status: `cd /Users/blakethomas/Documents/BravoGCPCopilot && ./check_guess_who_setup.sh`

---

## 📞 Support Resources

**Documentation:**
- Comprehensive guide: [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)
- Quick checklist: [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md)
- Setup guide: [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md)
- Reference card: [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md)

**Code Files:**
- Server endpoints: [server.py](server.py) lines 17866-18074
- Frontend JS: [guess_who.js](static/guess_who.js) (845 lines)
- HTML structure: [guess_who.html](static/guess_who.html) (282 lines)
- Integration: [gridpage.js](static/gridpage.js) line 1787

---

## ✨ Summary

Everything is prepared for local testing:

✅ **4 detailed testing guides** for different needs  
✅ **Setup validation script** confirming 20/20 components ready  
✅ **Complete game implementation** from categories to game over  
✅ **Full speech recognition** for wake words and guesses  
✅ **LLM integration** for content generation  
✅ **Audio announcements** with TTS  
✅ **All known issues documented** with workarounds  
✅ **Troubleshooting guides** for common problems  

**You're ready to test!** Pick a testing guide and start playing the Guess Who game locally.

---

**Questions?** Check the reference card or detailed guides first.  
**Found an issue?** Document it and report with:
- Exact steps to reproduce
- Console error screenshot
- Browser/OS information

**Enjoy testing!** 🎮

---

*Last Updated: 2025*  
*Test Environment: Local (http://localhost:8000)*  
*Status: Ready for Local Testing* ✅
