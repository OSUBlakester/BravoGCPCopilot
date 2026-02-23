# Guess Who Game - Quick Start Testing Checklist

## Pre-Test Setup
- [ ] Server is running: `python server.py` in terminal
- [ ] Terminal shows: `INFO: Uvicorn running on http://127.0.0.1:8000`
- [ ] Browser DevTools opened (F12)
- [ ] Console tab ready to check for errors
- [ ] Microphone is working and allowed in browser
- [ ] Test Firebase account is logged in

---

## Full Game Flow Test (5-10 minutes)

### Phase 1: Category Selection
- [ ] Navigate to http://localhost:8000/guess_who.html
- [ ] See "Select a Category" screen
- [ ] At least 5 categories display as buttons
- [ ] Home button visible in top-left
- [ ] No console errors (RED logs)

**Time:** 30 seconds

### Phase 2: Category Announcement & Mode Selection
- [ ] Click any category (e.g., "Movie Characters")
- [ ] Hear audio announcement of category name
- [ ] Mode selection screen appears with "You guess" and "I guess"
- [ ] Buttons properly spaced and readable

**Time:** 10 seconds + audio duration

### Phase 3: Mode A Selection (You Guess)
- [ ] Click "You guess" button
- [ ] Hear announcement: "See if you can guess who I am thinking of..."
- [ ] Wait for person generation
- [ ] See 6-10 person names as buttons (from selected category)
- [ ] No console errors

**Time:** 30 seconds + LLM generation time

### Phase 4: Person Selection
- [ ] Click any person (e.g., "Tom Hanks")
- [ ] Hear announcement: "I've made my selection..."
- [ ] Wait for clue generation
- [ ] Clue screen appears showing:
  - Target: [Person Name]
  - Clues Given: 0
  - Guesses Left: 3

**Time:** 30 seconds + LLM generation time

### Phase 5: Clue Selection & Wake Word Prompt
- [ ] Click any clue (e.g., "Known for adventure movies")
- [ ] Hear announcements:
  1. "Clue 1: [Your Selected Clue]"
  2. "Say hey bravo when you are ready to guess."
- [ ] Speech recognition is active (listening mode)
- [ ] Clue count updates to 1

**Time:** 15 seconds

### Phase 6: Wake Word Detection
- [ ] Speak the wake word phrase: "hey bravo"
- [ ] Hear announcement: "Listening for your guess"
- [ ] Speech recognition switches to guess mode
- [ ] No console errors

**Time:** 5 seconds + speech processing

### Phase 7: Guess Capture
- [ ] Speak a guess (e.g., "Is it Tom Hanks?")
- [ ] Guess screen appears showing:
  - "Player 2 guessed: [Your Guess]"
  - Guesses Left: 2 (decreased from 3)
  - 6 response option buttons

**Time:** 5 seconds + LLM generation (up to 3 seconds)

### Phase 8: Response Selection (Choose Incorrect)
- [ ] Click any "No" or incorrect response
- [ ] Response is announced
- [ ] Return to Clue screen
- [ ] Clues Given: 1 (unchanged)
- [ ] Guesses Left: 2 (reflects used guess)

**Time:** 10 seconds

### Phase 9: Second Guess (Choose Incorrect Again)
- [ ] Click another clue (or same clue)
- [ ] Hear clue announcement and wake word prompt
- [ ] Speak wake word: "hey bravo"
- [ ] Speak another guess
- [ ] Select "No" response
- [ ] Return to clue screen
- [ ] Guesses Left: 1

**Time:** 1 minute

### Phase 10: Final Guess Leading to Loss
- [ ] Select one more clue
- [ ] Make final guess with wake word
- [ ] Select "No" response
- [ ] Game Over screen appears showing:
  - "Game Over! I was thinking of: [Person Name]"
  - List of guesses attempted
  - "Play Again" or "Home" button

**Time:** 1 minute

**Total Test Time:** 5-10 minutes

---

## Quick Win Test (2 minutes - Alternative)

If you want to test quickly without going through full loss flow:

### Phase 1-5: Same as above (Category → Person → Clue)
- [ ] Category selected
- [ ] Person selected  
- [ ] Clue displayed

**Time:** 2 minutes

### Phase 6-7: Make Single Guess
- [ ] Speak wake word
- [ ] Make a guess
- [ ] On response screen, select any "Yes, correct!" option

**Time:** 30 seconds

### Phase 8: Game End - Win
- [ ] Game Over screen shows:
  - "You Won! Guessed in 1 try"
  - The selected person name

**Time:** 5 seconds

**Total Quick Test Time:** 2-3 minutes

---

## Known Issues to Expect

### ⚠️ Issue: LLM Response Spoilers
**What to watch for:** Response options might say things like "No, it's not Tom Hanks. That's actually Harrison Ford."

**Status:** Known, documented, not blocking

### ⚠️ Issue: Splash Screen Not Showing
**What to watch for:** No visual overlay/splash during announcements (when enabled in settings)

**Status:** Known, documented, not blocking

### ⚠️ Issue: Scanning Doesn't Stop Early
**What to watch for:** Button highlighting continues while announcement plays

**Status:** Known, documented, not blocking

---

## Error Quick-Reference

### Red Error: "authenticatedFetch is not defined"
- **Cause:** Browser not loading gridpage.js properly
- **Fix:** Refresh page, check network tab in DevTools
- **Location:** Check if guess_who.html has correct script imports

### Red Error: "announce is not defined"  
- **Cause:** Function not available in current context
- **Fix:** Ensure guess_who.js can access gridpage's announce() function
- **Solution:** May need to pass announce function as parameter

### Red Error: "Null reference on category-screen"
- **Cause:** HTML element IDs don't match JavaScript code
- **Fix:** Verify element IDs in guess_who.html exist and match selectors in JS

### Red Error: "SpeechRecognition not supported"
- **Cause:** Browser doesn't support Web Speech API
- **Fix:** Use Chrome, Edge, or Safari (not Firefox)
- **Workaround:** Manually type guess instead

### Yellow Warning: "Uncaught (in promise) RangeError"
- **Cause:** Grid column sizing issue
- **Fix:** Verify gridColumns setting is > 0 and < 20

---

## Quick Verification Checklist

**Audio/Microphone:**
- [ ] Microphone icon appears in address bar when speaking
- [ ] Audio plays smoothly (no stuttering)
- [ ] Volume is appropriate

**Speech Recognition:**
- [ ] Wake word detection works (tries multiple phonetic variations)
- [ ] Guess capture works (speech recognized as text)
- [ ] No errors when voice isn't clear

**UI/UX:**
- [ ] All buttons properly sized (not too large, not too small)
- [ ] Text is readable on all screens
- [ ] Grid layout matches configuration (default 6 columns)
- [ ] Home button always visible

**Game Logic:**
- [ ] Game state tracks correctly (clues, guesses)
- [ ] Win/loss conditions work
- [ ] Cannot make more than 3 guesses
- [ ] Cannot give more than 3 clues

**Integrations:**
- [ ] Settings load correctly (wake word, grid columns)
- [ ] LLM endpoints working (people, clues, responses)
- [ ] Audio endpoint working (/play-audio)
- [ ] Firebase auth working (correct user in sessionStorage)

---

## If Something Breaks

1. **Check console first** (F12 → Console tab)
2. **Look for RED errors**, note the exact message
3. **Check server terminal**, verify server is still running
4. **Refresh browser** (Ctrl+R or Cmd+R)
5. **Check network tab** (F12 → Network) for failed requests
6. **If still broken**, check the detailed testing guide: [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)

---

## Files to Review If Issues Occur

- **Backend:** `/Users/blakethomas/Documents/BravoGCPCopilot/server.py` (lines 17866-18074)
  - Check: `/api/guess-who/*` endpoints
  - Check: `_generate_gemini_content_with_fallback()` function

- **Frontend JS:** `/Users/blakethomas/Documents/BravoGCPCopilot/static/guess_who.js`
  - Check: `initializeGame()` entry point
  - Check: `showCategoryScreen()` for category loading
  - Check: Speech recognition setup functions

- **Frontend HTML:** `/Users/blakethomas/Documents/BravoGCPCopilot/static/guess_who.html`
  - Check: All 6 screen elements exist (category, mode, person, clue, guess, game-over)
  - Check: `.gridContainer` classes defined
  - Check: CSS for scanning highlight and button sizing

- **Integration:** `/Users/blakethomas/Documents/BravoGCPCopilot/static/gridpage.js`
  - Check: Line 1787 - Guess Who navigation
  - Check: `announce()`, `startAuditoryScanning()`, `authenticatedFetch()` functions exist

---

## Success Criteria

✅ **Test Passes if:**
1. No RED console errors during normal gameplay
2. All 10 phases complete without user intervention (except speech input)
3. Game state updates correctly (clues, guesses remaining)
4. Can reach both Win and Loss game end states
5. Home button works from any screen
6. Audio announcements play smoothly

❌ **Test Fails if:**
1. Console RED errors block gameplay
2. Required endpoints return 500+ errors
3. Speech recognition doesn't work
4. Game logic prevents reaching end state
5. User gets stuck on any screen

---

## After Testing

- [ ] Document any found issues
- [ ] Note any improvements for future
- [ ] Check if ready for test branch deployment
- [ ] Gather user feedback if applicable
- [ ] Plan next iteration (Mode B, multiplayer, etc.)
