# Guess Who Game - Local Testing Guide

## Overview
This guide provides step-by-step instructions to test the **Guess Who Mode A** game feature locally before deploying to the test branch.

## System Requirements
- Python 3.8+ (with FastAPI, Flask, Firebase Admin SDK installed)
- Node.js/npm (not required, but useful for local server management)
- Browser with Web Speech API support (Chrome/Edge/Safari recommended)
- Microphone access (for speech recognition wake word detection)
- Internet connection (to reach Firestore, Firebase Auth, Google Gemini API)

## Local Testing Setup

### 1. Start the FastAPI Server
Open a terminal in the workspace directory and run:
```bash
python server.py
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2. Access the Application
Open a web browser and navigate to:
```
http://localhost:8000/gridpage.html
```

### 3. Authenticate
You'll be redirected to login. Sign in with your test Firebase account.

### 4. Navigate to Guess Who
Once logged in:
1. Look for a "Games" or similar section in gridpage
2. Select "Guess Who" button (or navigate directly to http://localhost:8000/guess_who.html)

---

## Test Scenarios

### Scenario 1: Category Selection ✓
**Purpose:** Verify categories load and display correctly

**Steps:**
1. Start the game
2. Observe the category selection screen
3. Verify:
   - [ ] At least 5 categories display (Movie Characters, Animals, Sports Figures, US Presidents, etc.)
   - [ ] All buttons are visible and clickable
   - [ ] Home button appears at the top-left
   - [ ] Page title shows "Select a Category"

**Expected Result:**
- Categories load from `/api/guess-who/categories` endpoint
- Buttons use gridpage styling (rounded corners, shadows, proper spacing)
- Grid layout matches configured columns (default: 6 columns)

**Failure Points:**
- [ ] CORS error accessing /api/guess-who/categories → Check server.py endpoint
- [ ] No categories displayed → Check Firestore "categories" collection
- [ ] Buttons too large/small → Check gridColumns setting in /api/settings

---

### Scenario 2: Category Announcement & Mode Selection
**Purpose:** Verify category selection triggers announcement and shows mode options

**Steps:**
1. From category screen, click "Movie Characters" (or any category)
2. Listen for announcement (should say the category name)
3. Observe the mode selection screen
4. Verify:
   - [ ] Audio announcement plays (if audio enabled)
   - [ ] Mode screen displays with "You guess" and "I guess" buttons
   - [ ] Home button is visible

**Expected Result:**
- Category name is announced via TTS
- Mode screen appears with proper buttons
- Buttons are properly sized

**Failure Points:**
- [ ] No audio plays → Check /play-audio endpoint
- [ ] Announcement interrupted/stuttering → Check announcement queue logic
- [ ] Mode screen doesn't appear → Check updatePageContent() function

---

### Scenario 3: Game Mode Selection - "You Guess"
**Purpose:** Verify Mode A (player guesses) initializes correctly

**Steps:**
1. From mode selection screen, click "You guess"
2. Listen for announcement (should say "See if you can guess...")
3. Observe person selection screen
4. Verify:
   - [ ] 6-10 person names display
   - [ ] Each person is a clickable button
   - [ ] All people are from the selected category
   - [ ] Names are properly sized and readable

**Expected Result:**
- Announcement plays before person list loads
- `/api/guess-who/generate-people` endpoint is called
- Person buttons display with category-appropriate names

**Failure Points:**
- [ ] LLM error generating people → Check Gemini API key
- [ ] Persons not from correct category → Check LLM prompt in server.py
- [ ] No buttons display → Check response parsing in JavaScript

---

### Scenario 4: Person Selection & Clue Generation
**Purpose:** Verify Player 1 selects a person and clues are generated

**Steps:**
1. From person selection screen, click any person (e.g., "Tom Cruise")
2. Listen for announcement (should say "I've made my selection...")
3. Observe clue selection screen
4. Verify:
   - [ ] Clue screen shows: "Target: [Person Name]"
   - [ ] Shows "Clues Given: 0" and "Guesses Left: 3"
   - [ ] 5-6 clue options are displayed
   - [ ] Clues are contextually relevant to the person

**Expected Result:**
- Person is selected and announcement plays
- `/api/guess-who/generate-clues` endpoint is called
- Clues generate in real-time and display as buttons

**Failure Points:**
- [ ] Person not highlighted/selected → Check selectPerson() function
- [ ] No clues display → Check clue generation endpoint
- [ ] Clues don't match person → Check LLM prompt quality

---

### Scenario 5: Clue Selection & Wake Word Prompting
**Purpose:** Verify clue selection triggers wake word listening prompt

**Steps:**
1. From clue screen, click any clue (e.g., "Known for action movies")
2. Listen for announcements:
   - First: "Clue 1: [Selected Clue]"
   - Second: "Say [wake word] when you are ready to guess." (e.g., "Say hey bravo when you are ready to guess.")
3. Verify:
   - [ ] Both announcements play in sequence
   - [ ] Clue count increases (Clues Given: 1)
   - [ ] Speech recognition is active (listening for wake word)

**Expected Result:**
- Clue announced
- Wake word prompt given
- App switches to listening mode (waiting for wake word)

**Failure Points:**
- [ ] Audio cuts off mid-announcement → Check announcement queue
- [ ] No listening/speech recognition starts → Check setupWakeWordRecognition()
- [ ] Settings not loaded (wrong wake word) → Check loadGuessWhoSettings()

---

### Scenario 6: Wake Word Detection & Speech Recognition
**Purpose:** Verify player can trigger guessing mode with wake word

**Steps:**
1. From listening state (after clue announcement):
2. Say the configured wake word phrase (default: "hey bravo")
3. Verify:
   - [ ] Announcement plays: "Listening for your guess"
   - [ ] Speech recognition switches from wake word to guess capture
   - [ ] Microphone icon/indicator shows app is listening

**Expected Result:**
- Wake word is recognized
- App announces it's ready to listen for guess
- Speech recognition switches to guess mode

**Failure Points:**
- [ ] Wake word not recognized → Check microphone, try speaking clearly
- [ ] Speech doesn't switch modes → Check wake word detection logic
- [ ] Announcement doesn't play → Check audio queue

---

### Scenario 7: Guess Capture & Response Generation
**Purpose:** Verify player's guess is captured and response options are generated

**Steps:**
1. From listening state (after "Listening for your guess"):
2. Say a guess (e.g., "Is it Tom Cruise?")
3. Verify:
   - [ ] Guess screen displays with "Player 2 guessed: [Your Guess]"
   - [ ] Shows "Guesses Left: 2" (decreased from 3)
   - [ ] 6 response options appear (mix of correct/incorrect responses)
   - [ ] Each response is a clickable button

**Expected Result:**
- Speech is captured and parsed
- `/llm` endpoint generates response options using Gemini
- Guess screen displays with 6 response buttons
- Buttons are properly sized and readable

**Failure Points:**
- [ ] Guess not captured → Check microphone, speak clearly
- [ ] No response options generate → Check `/llm` endpoint
- [ ] Response options are inappropriate → Check LLM prompt
- [ ] Response options reveal the person → **BUG** (documented in KNOWN ISSUES)

---

### Scenario 8: Incorrect Guess Response & Clue Cycling
**Purpose:** Verify incorrect responses loop back to clue selection

**Steps:**
1. From response screen, click any "No" or incorrect response (e.g., "No, that's not it.")
2. Verify:
   - [ ] Response is announced
   - [ ] App returns to clue screen
   - [ ] Clue count remains same, Guesses Left decreases (now shows 1)
   - [ ] Can select another clue

**Expected Result:**
- Response announced to user
- Game loops back to clue selection
- Game state updates correctly (guesses remaining decreases)

**Failure Points:**
- [ ] Response not announced → Check audio queue
- [ ] Not returning to clue screen → Check game flow logic
- [ ] Guess counter not updating → Check gameState management

---

### Scenario 9: Correct Guess - Win Condition
**Purpose:** Verify game ends when correct response is selected

**Steps:**
1. Go through multiple clues and guesses until reaching a response marked as "is_correct: true"
2. Click the correct response (e.g., "Yes, that's correct!")
3. Verify:
   - [ ] Response is announced
   - [ ] Game Over screen displays
   - [ ] Shows "You Won! Guessed in [X] tries"
   - [ ] Shows the person that was selected
   - [ ] Contains "Play Again" or "Home" button

**Expected Result:**
- Correct response triggers endGame()
- Game Over screen shows win state
- User can restart or return home

**Failure Points:**
- [ ] Game doesn't end → Check is_correct evaluation
- [ ] Game over screen doesn't display → Check endGame() function
- [ ] Stats not calculated → Check gameState.gameResult

---

### Scenario 10: Loss Condition (All Guesses Used)
**Purpose:** Verify game ends when guesses are exhausted

**Steps:**
1. Make 3 incorrect guesses (use "No" responses for each)
2. On 3rd incorrect guess, verify:
   - [ ] Game Over screen displays
   - [ ] Shows "Game Over. I was thinking of: [Person Name]"
   - [ ] Shows guesses attempted list
   - [ ] Contains "Play Again" or "Home" button

**Expected Result:**
- Game ends after 3 incorrect guesses
- Game Over screen reveals the person
- Shows list of attempted guesses

**Failure Points:**
- [ ] Game continues after 3 guesses → Check guessesRemaining logic
- [ ] Person not revealed → Check gameState.selectedPerson
- [ ] Guess list not shown → Check guess history tracking

---

### Scenario 11: Home Navigation
**Purpose:** Verify Home button works from any screen

**Steps:**
1. From any screen in Guess Who (category, person, clue, guess, game over):
2. Click the Home button (top-left)
3. Verify:
   - [ ] Returns to gridpage.html
   - [ ] Game state is reset
   - [ ] No errors in console

**Expected Result:**
- Cleanly exits Guess Who
- Returns to gridpage without errors

**Failure Points:**
- [ ] Home button doesn't navigate → Check createHomeButton() function
- [ ] console.js errors → Check cleanup/state reset

---

### Scenario 12: Settings Integration
**Purpose:** Verify user settings affect game behavior

**Steps:**
1. Before starting game, set user settings:
   - `scanDelay`: 2000 (milliseconds)
   - `wakeWordInterjection`: "hey"
   - `wakeWordName`: "assistant"
   - `gridColumns`: 3

2. Start Guess Who and verify:
   - [ ] Categories display in 3-column grid (not 6)
   - [ ] Button fonts are larger (due to fewer columns)
   - [ ] Wake word is "hey assistant" (not "hey bravo")
   - [ ] Scanning delay matches 2000ms

**Expected Result:**
- Settings load correctly from `/api/settings`
- Game behavior adjusts based on user preferences

**Failure Points:**
- [ ] Settings don't load → Check loadGuessWhoSettings()
- [ ] Incorrect wake word used → Check getWakeWordPhrase()
- [ ] Grid columns not applied → Check gridColumns usage

---

## Browser Console Testing

### Check Logs
1. Open Browser DevTools (F12)
2. Go to Console tab
3. Verify no RED errors appear during gameplay
4. Expected INFO logs:
   - "Initializing Guess Who game"
   - "showCategoryScreen"
   - "Received categories"
   - "Starting wake word listener"

### Common Errors to Debug

**Error: "authenticatedFetch is not defined"**
- Solution: Ensure guess_who.html links to gridpage.html (imports authenticatedFetch)
- Check: `<script src="gridpage.js"></script>` in guess_who.html

**Error: "announce is not defined"**
- Solution: announce() is called from gridpage.js
- Check: Ensure correct parent window context or pass in function

**Error: "Null pointer on element"**
- Solution: Check element IDs in HTML match JavaScript references
- Find: Search for `getElementById`, `querySelector` calls in console output

**Error: "CORS error on /api/guess-who/*"**
- Solution: Check ALLOWED_ORIGINS in server.py
- Fix: Add `http://localhost:8000` to ALLOWED_ORIGINS

**Error: "No categories found"**
- Solution: Check Firestore database
- Verify: "categories" collection exists with documents containing category names

---

## Performance Testing

### Measure Response Times
1. Open DevTools Network tab
2. Play through a full game round
3. Check response times for:
   - `/api/guess-who/categories`: Should be < 500ms
   - `/api/guess-who/generate-people`: Should be < 2000ms (LLM call)
   - `/api/guess-who/generate-clues`: Should be < 2000ms (LLM call)
   - `/llm` (for response options): Should be < 3000ms (LLM call)
   - `/play-audio`: Should be < 500ms

### Check Audio Playback
1. Verify TTS audio plays smoothly
2. Check for audio stuttering/buffering
3. Verify volume levels are appropriate

---

## Known Issues to Track

### Issue 1: LLM Response Options May Contain Spoilers
**Status:** Documented
**Description:** Response options sometimes reveal the selected person even when the guess is wrong.
**Example:** "No, that's Detective Holmes" when the guess was wrong
**Workaround:** Select generic responses without spoilers
**Fix:** Update LLM prompt to explicitly forbid revealing the person

### Issue 2: Splash Screen Not Integrated
**Status:** Documented
**Description:** Splash Screen (configurable UI overlay) doesn't appear during announcements
**Workaround:** None - visual feedback missing during announcements
**Fix:** Integrate showSplashScreen() call in announce() function

### Issue 3: Scanning Doesn't Stop Before Announcement
**Status:** Documented
**Description:** Button highlighting (scanning) continues until selection completes instead of stopping immediately
**Workaround:** None - minor UX issue
**Fix:** Call stopAuditoryScanning() before announceText()

---

## Pass/Fail Criteria

### Must Pass (Blocking)
- [x] Categories load and display
- [x] Mode selection works
- [x] Person selection initiates clue generation
- [x] Clues generate and display
- [x] Wake word triggers guess listening
- [x] Guess is captured via speech recognition
- [x] Response options generate
- [x] Game ends on correct guess
- [x] Game ends on 3 incorrect guesses
- [x] No console errors during normal gameplay

### Should Pass (Critical)
- [ ] Splash Screen appears during announcements (KNOWN ISSUE)
- [ ] Scanning stops before announcement (KNOWN ISSUE)
- [ ] LLM responses don't reveal person (KNOWN ISSUE)
- [ ] Settings load correctly
- [ ] Home navigation works

### Nice to Have (Enhancements)
- [ ] Audio volume control
- [ ] Option to repeat last announcement
- [ ] Skip clue selection
- [ ] View statistics (win rate, etc.)

---

## Test Report Template

```markdown
# Test Report - Guess Who Mode A

**Date:** [Date]
**Tester:** [Name]
**Environment:** Local (http://localhost:8000)
**Category Tested:** [e.g., Movie Characters, Animals]
**Browser:** [e.g., Chrome 120, Safari 17]

## Results Summary
- Categories: ✓/✗
- Mode Selection: ✓/✗
- Person Selection: ✓/✗
- Clue Generation: ✓/✗
- Wake Word Detection: ✓/✗
- Guess Capture: ✓/✗
- Response Options: ✓/✗
- Win Condition: ✓/✗
- Loss Condition: ✓/✗

## Issues Found
1. [Issue 1]
2. [Issue 2]

## Notes
[Additional observations]
```

---

## Next Steps After Local Testing
1. ✅ Pass local testing on multiple browsers
2. Document any new issues
3. Create pull request to test branch
4. Deploy to test environment
5. Conduct user acceptance testing (UAT)
6. Deploy to production

---

## Support

**Questions?**
- Check console logs first (F12 → Console)
- Verify server is running (check terminal output)
- Check Firestore data is populated
- Review error messages in browser

**To Report Issues:**
Create a detailed report with:
1. Steps to reproduce
2. Expected vs. actual behavior
3. Console errors (screenshot or copy)
4. Browser/OS information
5. Category and person being tested
