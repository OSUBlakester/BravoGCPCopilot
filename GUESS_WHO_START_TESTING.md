# Guess Who Game - Local Testing Setup Instructions

## ✅ Pre-flight Checks (All Passing!)

Your setup has been validated. All 20 component checks passed:
- ✓ All required files present (server.py, guess_who.html, guess_who.js, gridpage.js)
- ✓ Backend endpoints configured (/api/guess-who/*)
- ✓ Frontend functions available (authenticatedFetch, announce, startAuditoryScanning)
- ✓ Audio system ready (/llm, /play-audio endpoints)
- ✓ All dependencies installed (FastAPI, Firebase Admin SDK, Google Generative AI)
- ✓ All 6 game screens defined in HTML
- ✓ Grid layout and scanning CSS configured

**Status:** 🟢 READY FOR LOCAL TESTING

---

## Step 1: Start the FastAPI Server

Open a new terminal window in the workspace directory and run:

```bash
cd /Users/blakethomas/Documents/BravoGCPCopilot
python3 server.py
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**⚠️ If you see errors:**
- **"Port already in use"**: Close other local servers or use `lsof -i :8000` to find what's using port 8000
- **"ModuleNotFoundError"**: Run `pip3 install -r requirements.txt` or install missing packages
- **"GOOGLE_API_KEY not found"**: Ensure `.env` file has GOOGLE_API_KEY or set environment variable

**Keep this terminal open** throughout testing. Do not close it.

---

## Step 2: Open Browser and Login

1. Open a new browser tab (Chrome, Safari, or Edge recommended)
2. Navigate to: **http://localhost:8000/gridpage.html**
3. You'll be redirected to login page
4. Sign in with your test Firebase account

**Expected:**
- Login page with Firebase Sign In options
- Redirects to gridpage main interface after authentication
- No "localhost refused to connect" errors

---

## Step 3: Navigate to Guess Who

Option A: Using Navigation Button
1. Once logged into gridpage, look for "Games" section or similar
2. Find and click "Guess Who" button
3. Should navigate to guess_who.html

Option B: Direct URL
1. In the address bar, navigate directly to: **http://localhost:8000/guess_who.html**
2. Should load the game immediately if already authenticated

**Expected:**
- Category selection screen loads
- "Select a Category" title displays
- 5+ category buttons visible

---

## Step 4: Open Developer Tools

Open browser Developer Tools to monitor for errors:

**Chrome/Edge:**
- Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Shift+I` (Mac)

**Safari:**
- Enable in Preferences > Advanced > Show Develop menu
- Press `Cmd+Option+I`

Switch to **Console** tab:
- Look for any RED error messages
- Watch for network requests to API endpoints
- Monitor for JavaScript warnings

---

## Step 5: Start Testing

Choose one of the testing scenarios:

### Quick Test (2-3 minutes)
- Test just the basic flow: Category → Mode → Person → Clue
- See if all buttons load and styling looks correct
- Check if clue generation works
- See the detailed checklist: [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md)

### Full Test (10-15 minutes)
- Complete entire game flow from category selection to game over
- Test both win condition (correct guess) and loss condition (all guesses used)
- Test home navigation from various screens
- See the detailed scenarios: [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)

---

## During Testing: What to Monitor

### Browser Console (Most Important)
Check for RED error messages:
- `authenticatedFetch is not defined` → Page loading issue
- `Cannot read property 'textContent' of null` → HTML element not found
- `SpeechRecognition is not defined` → Browser doesn't support (try Chrome)
- `CORS error` → Server ALLOWED_ORIGINS problem
- `404 Not Found` → Endpoint doesn't exist

### Network Tab (Optional)
Check request/response times:
- `/api/guess-who/categories` → Should be < 500ms
- `/api/guess-who/generate-people` → Should be < 3000ms (LLM call)
- `/api/guess-who/generate-clues` → Should be < 3000ms (LLM call)
- `/llm` → Should be < 4000ms (LLM response options)
- `/play-audio` → Should be < 1000ms

**Red indicators (4xx/5xx status codes):**
- Setup issue → Check server.py
- Config issue → Check environment variables
- Database issue → Check Firestore permissions

### Server Terminal
Watch for error messages:
- `KeyError: 'xyz'` → Missing field in request/response
- `TypeError` → Data type mismatch
- `ConnectionError` → Can't reach Firestore or Gemini API
- `AttributeError` → Function/module doesn't exist

---

## Testing Speech Recognition

### Browser Microphone Permission
When speech recognition starts, you'll see a prompt to allow microphone access:
- Click "Allow" to grant permission
- Only happens once, then remembered for localhost

### Testing Wake Word Detection
1. After selecting a clue, you'll hear: "Say [wake word] when you are ready to guess."
2. Speak clearly: **"hey bravo"** (or your configured wake word)
3. Should hear: "Listening for your guess"

**If wake word not detected:**
- [ ] Speak more slowly and clearly
- [ ] Increase microphone volume
- [ ] Try alternative phonetic: "hey, bravo" (with comma)
- [ ] Check console for speech recognition errors

### Testing Guess Recognition
1. After wake word is recognized, speak your guess clearly
2. Example: **"Is it Tom Hanks?"** or just **"Tom Hanks"**
3. Should display guess on screen with response options

**If guess not captured:**
- [ ] Speak longer phrases (single words may not register)
- [ ] Increase microphone volume
- [ ] Check console for SpeechRecognition errors
- [ ] Ensure continuous=false in speech recognition config

---

## If You Encounter Issues

### Issue: "authenticatedFetch is not defined"
**Cause:** gridpage.js not loaded properly

**Solution:**
1. Check Network tab (F12 → Network) - look for gridpage.js request
2. If 404: File path is wrong in HTML
3. If loaded: Might be a scoping issue with how announce() is called
4. Try: Refresh page, check browser console for load order

**Next Steps:** Review guess_who.html script order, ensure gridpage.js loads before guess_who.js

### Issue: "Null reference on category-screen"
**Cause:** HTML element with that ID doesn't exist

**Solution:**
1. Open guess_who.html in editor
2. Search for `id="category-screen"`
3. Verify element exists and has correct ID
4. Check for typos in JavaScript selectors vs HTML IDs

**Next Steps:** Compare console error line number with actual HTML structure

### Issue: Speech Recognition Says "not supported"
**Cause:** Browser doesn't have Web Speech API

**Solution:**
1. Switch to Chrome or Edge (best support)
2. Try Safari (also has good support)
3. Firefox doesn't support Web Speech API - not compatible

**Next Steps:** Use Chrome/Edge for local testing

### Issue: Microphone Not Working
**Cause:** Permission denied or no input device

**Solution:**
1. Check browser microphone permission:
   - Address bar → Click microphone icon → Check permissions
   - May need to allow localhost:8000
2. Check system microphone:
   - macOS: System Preferences > Security & Privacy > Microphone
   - See if microphone is listed for browser
3. Test microphone in another app (Voice Memos, etc.)

**Next Steps:** Grant microphone permission to browser and system

### Issue: No Categories Appear
**Cause:** API endpoint error or Firestore empty

**Solution:**
1. Check server terminal for errors
2. Check browser Network tab:
   - Look for `/api/guess-who/categories` request
   - Check status code (should be 200)
   - Look at response in "Response" tab
3. If 500 error:
   - Firestore connection issue
   - GOOGLE_APPLICATION_CREDENTIALS not set
   - Categories collection empty in Firestore

**Next Steps:** Verify Firestore has categories data, check server.py logs

### Issue: LLM Generation Fails (People, Clues, Responses)
**Cause:** Google Gemini API key invalid or API quota exceeded

**Solution:**
1. Check console for specific error message
2. Verify GOOGLE_API_KEY in .env file
3. Check Google AI Studio: https://aistudio.google.com/
4. Ensure API is enabled in GCP project
5. Check if quota is exceeded (rate limit)

**Next Steps:** Verify API key, check GCP project permissions, wait if rate limited

### Issue: Audio Not Playing
**Cause:** /play-audio endpoint error or audio context not resumed

**Solution:**
1. Check Network tab for `/play-audio` requests
2. Look for 200 status and audio data in response
3. Browser may require user gesture to play audio (click button first)
4. Check browser volume (not muted)
5. Check speaker permissions (particularly on macOS)

**Next Steps:** Ensure speakers are working, check if audio plays in other apps

---

## Common Fixes Quick Reference

| Symptom | Quick Fix |
|---------|-----------|
| Page won't load | Refresh browser, check server is running |
| Console errors about functions | Clear sessionStorage: Press F12, then `sessionStorage.clear()`, refresh |
| Buttons very large/small | Check gridColumns setting in user profile settings |
| Wake word not detected | Speak more clearly, increase microphone volume |
| No audio plays | Check speaker volume, microphone may need permission |
| Freezes on person selection | Server may be slow - check LLM generation time |
| Game won't proceed | Check console for errors, try Home button to restart |

---

## Testing Checklist

Before starting full test, check these boxes:

**Setup:**
- [ ] Server running: `python3 server.py` (terminal shows "Uvicorn running")
- [ ] Browser tab open: `http://localhost:8000/gridpage.html`
- [ ] Logged in with Firebase account
- [ ] DevTools open (F12) with Console tab active
- [ ] Microphone allowed in browser

**Quick Validation (< 1 minute):**
- [ ] Navigate to Guess Who
- [ ] See category selection screen
- [ ] Click any category
- [ ] Hear category announcement
- [ ] See mode selection screen

**Full Test (10-15 minutes):**
- [ ] Follow [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md) or [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)
- [ ] Note any errors in console
- [ ] Document any unexpected behavior
- [ ] Test both win and loss scenarios

---

## After Testing

### Successful Testing ✅
If testing completes without RED console errors:
1. Create a new test report
2. Note any warnings or quirks observed
3. Check if ready for test branch deployment
4. Plan next improvements (Mode B, multiplayer, etc.)

### Issues Found ❌
If you encounter RED console errors:
1. Document the exact error message
2. Note steps to reproduce
3. Check the [Comprehensive Testing Guide](GUESS_WHO_LOCAL_TEST.md) for that specific issue
4. Review server.py logs for backend errors
5. Create GitHub issue with:
   - Error message (screenshot)
   - Steps to reproduce
   - Browser/OS info
   - Network tab findings

### Known Issues (Not Blocking)
These are documented but don't block testing:
- [ ] LLM sometimes reveals person name in response (known issue)
- [ ] Splash Screen doesn't appear during announcements (planned fix)
- [ ] Scanning doesn't stop before announcement (minor UX issue)

---

## Next Steps

### When Testing is Done
1. Document results in test report
2. Gather feedback on UX/gameplay
3. Make improvements based on findings
4. Deploy to test branch: `git push origin local-testing:test`
5. Conduct user acceptance testing (UAT)

### Future Enhancements
- [ ] Mode B (I guess - AI plays against human)
- [ ] Multiplayer support (both players in same room)
- [ ] Category/person management UI
- [ ] Game statistics tracking
- [ ] Hint system improvements
- [ ] Sound effects and background music

---

## Support Resources

**Detailed Guides:**
- [Full Testing Guide with 12 Scenarios](GUESS_WHO_LOCAL_TEST.md)
- [Quick Test Checklist (2 min version)](GUESS_WHO_QUICK_TEST.md)

**Code Files:**
- Backend: [server.py](server.py) (lines 17866-18074 for Guess Who endpoints)
- Frontend JS: [guess_who.js](static/guess_who.js) (845 lines)
- Frontend HTML: [guess_who.html](static/guess_who.html) (282 lines)
- Integration: [gridpage.js](static/gridpage.js) (line 1787 navigation)

**Key Functions:**
- `initializeGame()` - Entry point
- `showCategoryScreen()` - Category selection
- `startModeA()` - Begin Mode A game
- `selectPerson()` - Player 1 picks secret person
- `selectClue()` - Give clue to Player 2
- `startWakeWordListener()` - Listen for wake word
- `handleGuessHeard()` - Process Player 2's guess
- `handleGuessResponse()` - Evaluate guess correctness

**API Endpoints:**
- `POST /api/guess-who/categories` - Get all categories
- `POST /api/guess-who/generate-people` - Generate people for category
- `POST /api/guess-who/generate-clues` - Generate clues for person
- `POST /llm` - Generate guess response options
- `POST /play-audio` - Text-to-speech audio
- `GET /api/settings` - Load user settings

---

## Keyboard Shortcuts During Testing

**Browser DevTools:**
- `F12` - Open DevTools
- `Ctrl+Shift+J` (Windows) or `Cmd+Option+J` (Mac) - Jump to Console
- `Ctrl+Shift+N` (Windows) or `Cmd+Option+N` (Mac) - Jump to Network
- `Ctrl+K` or `Cmd+K` - Clear console

**During Game:**
- `Ctrl+R` or `Cmd+R` - Refresh page
- `Ctrl+Shift+R` - Hard refresh (clear cache)
- `Alt+Left Arrow` - Go back
- `F5` - Full page reload

---

**Good luck with testing! Document your findings and report any issues found.** 🎮

Start with the Quick Test (2 min) to validate basic flow, then do Full Test (15 min) for complete coverage.

Ready? Start the server now: `python3 server.py`
