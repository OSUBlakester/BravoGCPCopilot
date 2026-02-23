# Guess Who Game - Tester's Reference Card

**Quick reference during local testing. Print this page or keep it in another window.**

---

## 🎮 Game Flow Overview

```
Category Selection
↓
Mode Selection (You guess / I guess)
↓
Mode A Selected (You guess)
↓
Person Selection (P1 picks)
↓
Clue Selection (P1 gives clue)
↓
Wake Word Trigger (P2 says wake word)
↓
Guess Capture (P2 speaks guess)
↓
Response Options (P1 picks response)
↓
Check Correct?
├─ YES → WIN (Game Over)
└─ NO → Check guesses left?
    ├─ > 0 → Back to Clue Selection
    └─ 0 → LOSS (Game Over)
```

---

## 🔊 Wake Word Phrases

**Default:** "hey bravo"

**Variations the system will accept:**
- "hey bravo"
- "hey, bravo" (with comma)
- "hey,bravo" (without space after comma)

**To change wake word:**
- User Settings → Wake Word Interjection + Wake Word Name
- Default: Interjection = "hey", Name = "bravo"
- Examples: "hello buddy", "hey assistant", etc.

---

## 🎤 Speech Testing

| Scenario | What to Say | Expected Response |
|----------|-------------|-------------------|
| Wake word | "hey bravo" | "Listening for your guess" |
| Simple guess | "Tom Hanks" | Displays guess on screen |
| Question guess | "Is it Tom Hanks?" | Displays guess on screen |
| Multi-word guess | "Captain America Marvel" | Displays guess on screen |

---

## 🔴 Error Codes & Quick Fixes

### RED Console Errors (STOP and Fix)

| Error | Cause | Fix |
|-------|-------|-----|
| `authenticatedFetch is not defined` | Missing gridpage.js | Refresh page, check browser cache |
| `Cannot read property of null` | HTML element missing | Check HTML IDs match JavaScript |
| `SpeechRecognition not defined` | Old browser | Use Chrome, Safari, or Edge |
| `CORS error` | Server blocked request | Check ALLOWED_ORIGINS in server.py |
| `404 Not Found /api/guess-who/*` | Endpoint missing | Restart server, check server.py |

### YELLOW Warnings (Continue but Monitor)

| Warning | Meaning | Impact |
|---------|---------|--------|
| "Uncaught (in promise) RangeError" | Grid sizing issue | Buttons may be too large/small |
| "Failed to fetch" | Network timeout | Slow LLM generation |
| "Microphone permission denied" | Browser blocked mic | Speech recognition won't work |

---

## 📊 Expected Performance

| Operation | Time | Status |
|-----------|------|--------|
| Category load | < 0.5s | Should be instant |
| Mode selection | < 0.1s | Immediate |
| Generate people | 1-3s | Slow (LLM) - OK |
| Person selection | < 0.1s | Immediate |
| Generate clues | 1-3s | Slow (LLM) - OK |
| Clue announcement | < 2s | Audio TTS generation |
| Wake word detect | Variable | Depends on speech |
| Guess capture | 2-5s | Waiting for complete phrase |
| Generate responses | 1-3s | Slow (LLM) - OK |
| Response announcement | < 2s | Audio TTS |

**Rule:** If operation takes < 5s, it's normal. 5-10s is slow but acceptable.

---

## 🎯 Success Criteria Checklist

Before marking test as PASS, verify:

**✅ Must Pass:**
- [ ] No RED console errors block gameplay
- [ ] Can reach all 6 screens (category → mode → person → clue → guess → game-over)
- [ ] Wake word detection works (detects "hey bravo" variations)
- [ ] Speech recognition captures guesses
- [ ] Game correctly identifies win/loss
- [ ] Home button works from any screen
- [ ] Can restart game multiple times

**⚠️ Should Pass (Can have known issues):**
- [ ] Grid layout matches configured columns
- [ ] Button text readable (font size appropriate)
- [ ] Audio plays without stuttering
- [ ] Settings load correctly (scan delay, wake word, grid columns)
- [ ] Loading indicators appear during LLM calls

---

## 🐛 Common Issues During Testing

### "Categories won't load"
1. Check Network tab → `/api/guess-who/categories` request
2. Look at status code (200 = OK, 500 = server error, 404 = missing)
3. If 500: Check server terminal for errors
4. If 404: Endpoint not defined in server.py
5. **Quick fix:** Restart server, clear browser cache

### "Wake word not detected"
1. Speak clearly: "hey bravo" (not too fast, not too slow)
2. Check microphone volume (try other app first)
3. Look in console for Speech Recognition errors
4. Try alternative phrasing: "hey, bravo" (with comma)
5. **Quick fix:** Refresh page, reload speech recognition

### "No response options appear"
1. Check Network tab → `/llm` request
2. Look for 200 status and JSON response
3. If 500: Check server logs for LLM error
4. If timeout: Gemini API may be slow or quota exceeded
5. **Quick fix:** Wait a few seconds, try again

### "Audio cutoff or stuttering"
1. Check speaker volume in system settings
2. Check app volume (if OS per-app volume exists)
3. Look for `/play-audio` requests in Network tab
4. May be concurrent audio requests - check timing
5. **Quick fix:** Close other audio apps, increase speaker volume

### "Buttons extremely large or tiny"
1. Check user settings: gridColumns value
2. Default is 6 columns
3. If very large: gridColumns may be 2-3
4. If very tiny: gridColumns may be 10+
5. **Quick fix:** Adjust gridColumns in settings

---

## 📱 Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome | ✅ Full | Best experience, all features work |
| Edge | ✅ Full | Same as Chrome, all features work |
| Safari | ✅ Full | Might need permission prompt for mic |
| Firefox | ❌ No | Web Speech API not supported |
| Opera | ✅ Partial | May have audio issues |

**Recommended:** Use Chrome or Edge for testing.

---

## 🎥 Recording Test Results

**If asked to document:**

1. **Screenshot categories screen**
   - Shows categories loading properly

2. **Screenshot mode selection**
   - Shows Mode A (You guess) option

3. **Screenshot clue screen**
   - Shows selected person and clue count

4. **Screenshot guess response**
   - Shows captured guess and response options

5. **Screenshot game over**
   - Shows win or loss state with stats

6. **Console log** (F12 → Console)
   - No RED errors (or document any found)

---

## 🔧 Debug Mode - If Things Break

**Enable console logging (in browser DevTools):**

```javascript
// Copy-paste into console (F12) to see detailed logs:

// Check current game state
console.log(gameState);

// Check if recognize API is available
console.log(window.SpeechRecognition || window.webkitSpeechRecognition);

// Check if authenticate is working
console.log('Token:', sessionStorage.getItem('firebaseIdToken'));

// Check settings
console.log('Scan delay:', defaultDelay);
console.log('Wake word:', wakeWordInterjection, wakeWordName);
console.log('Grid columns:', gridColumns);

// Clear session (forces re-login)
sessionStorage.clear();
location.reload();
```

---

## ⏱️ Testing Timeline

**Recommended testing schedule:**

| Phase | Duration | Activities |
|-------|----------|------------|
| Setup | 5 min | Start server, verify components |
| Quick Test | 2-3 min | Category → Person → Clue flow |
| Full Test | 10-15 min | Complete game flow with win/loss |
| Stress Test | 5-10 min | Rapid category switches, multiple games |
| Bug Hunt | 10-15 min | Intentional edge cases (fast speech, etc.) |
| **Total** | **35-50 min** | Complete testing session |

---

## 👤 Tester Notes

**Name:** ________________  
**Date:** ________________  
**Browser:** ________________  
**Category Tested:** ________________  

**Issues Found:**
1. ___________________________________
2. ___________________________________
3. ___________________________________

**Notes:**
_______________________________________________
_______________________________________________

---

## 📞 Getting Help

**If stuck:**
1. Check console (F12 → Console) for error message
2. Look up error in this card or [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)
3. Check Network tab (F12 → Network) for failed requests
4. Restart server and clear browser cache
5. Review [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) for detailed setup

**To report issues:**
- Exact steps to reproduce
- Screenshot of console error
- Browser and OS information
- Expected vs. actual behavior

---

## 🎮 Quick Game Loop (Manual Test)

**Test a single game round in < 2 minutes:**

1. Start game, click "Movie Characters"
2. Click "You guess"
3. Click any person (e.g., "Tom Hanks")
4. Click any clue
5. Say "hey bravo"
6. Say "Is he an actor?"
7. Click any "No" response
8. Repeat clue selection 2 more times
9. When out of guesses, see Game Over

**Success:** All steps complete without RED errors.

---

## 🔑 Key Endpoints (For Reference)

```
POST /api/guess-who/categories
  Request: {}
  Response: { "all_categories": ["Movie Characters", ...] }

POST /api/guess-who/generate-people
  Request: { "category": "Movie Characters", "previous_people": [] }
  Response: { "people": ["Tom Hanks", ...] }

POST /api/guess-who/generate-clues
  Request: { "category": "...", "selected_person": "...", "previous_clues": [] }
  Response: { "clues": ["An actor", ...] }

POST /llm
  Request: { "prompt": "..." }
  Response: [{ "text": "...", "summary": "...", "is_correct": true/false }, ...]

POST /play-audio
  Request: { "text": "Hello" }
  Response: { "audio": "<base64>", "sampleRate": 24000 }

GET /api/settings
  Request: (auth token required)
  Response: { "scanDelay": 3500, "wakeWordInterjection": "hey", ... }
```

---

## 💡 Pro Tips for Testing

1. **Keep DevTools open** - Catch errors immediately
2. **Test voice clearly** - AI speech recognition needs good input
3. **Wait for LLM** - Generation can take 2-3 seconds
4. **Fresh browser** - Clear cache between major tests
5. **Multiple categories** - Test at least 3 different categories
6. **Multiple guesses** - Test both correct and incorrect paths
7. **Test navigation** - Use Home button from each screen
8. **Check responsive** - Try different screen sizes
9. **Note timings** - Slow responses help identify issues
10. **Document findings** - Write notes for each test

---

**Good luck! Have fun testing the Guess Who game! 🎮**

Remember: You're testing for completeness and bugs. If something feels wrong, it probably is. Document it!
