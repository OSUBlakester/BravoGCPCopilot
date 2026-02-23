# Guess Who Game - Testing Documentation Index

**Quick Links to All Testing Resources**

---

## 📚 Documentation Files

### Quick Access by Need

**I want to start testing NOW** → [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md)
- Step-by-step setup instructions
- How to start server
- How to navigate to game
- First-time troubleshooting

**I want a quick 2-minute test** → [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md)
- Quick game flow (5-10 min)
- Quick win scenario (2-3 min)
- Known issues to expect
- Success criteria

**I want thorough testing** → [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)
- 12 detailed test scenarios
- Each with steps, expected results, failure points
- Performance benchmarks
- Complete pass/fail criteria

**I need quick reference during testing** → [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md)
- Print-friendly one-page card
- Game flow diagram
- Error codes and quick fixes
- Browser compatibility
- Pro tips

**I want complete overview** → [GUESS_WHO_LOCAL_TEST_COMPLETE.md](GUESS_WHO_LOCAL_TEST_COMPLETE.md)
- What was prepared
- Architecture overview
- Component status
- Known issues
- Next steps

**I need to validate setup** → Run: `./check_guess_who_setup.sh`
- Checks 20 components
- Verifies files exist
- Confirms dependencies installed
- Validates endpoints present

---

## 🎯 Testing by Scenario

### Scenario: "I have 5 minutes"
1. Read: [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) - Step 1-2 (2 min)
2. Run: `python3 server.py` (1 sec)
3. Navigate: http://localhost:8000/guess_who.html (1 min)
4. Test: Click category, then mode (1 min)
5. Result: See if basic flow works

**Documentation:** [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md) Phase 1-2

---

### Scenario: "I have 30 minutes"
1. skim: [GUESS_WHO_LOCAL_TEST_COMPLETE.md](GUESS_WHO_LOCAL_TEST_COMPLETE.md) (2 min)
2. Setup: Follow [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) (3 min)
3. Test: [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md) full flow (10 min)
4. Document: Note any issues (5 min)
5. Review: Check reference card for anything missed (5 min)

**Documentation:** All files, but prioritize Quick Test

---

### Scenario: "I have 1 hour"
1. Read: [GUESS_WHO_LOCAL_TEST_COMPLETE.md](GUESS_WHO_LOCAL_TEST_COMPLETE.md) (5 min)
2. Setup: [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) (5 min)
3. Test: [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) Scenarios 1-5 (20 min)
4. Test: [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) Scenarios 6-10 (20 min)
5. Document: Findings and next steps (5 min)

**Documentation:** Use all files in order

---

### Scenario: "Something broke"
1. Check: [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md) Common Issues (2 min)
2. Validate: `./check_guess_who_setup.sh` (1 min)
3. Research: [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) Troubleshooting (5 min)
4. Deep dive: [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) relevant scenario (10 min)

**Documentation:** Reference card + troubleshooting guide

---

## 🔧 Code Files to Review

If specific feature isn't working:

| Feature | File | Lines | When |
|---------|------|-------|------|
| Categories endpoint | server.py | 17866-17905 | Categories won't load |
| People generation | server.py | 17906-17994 | Person selection fails |
| Clues generation | server.py | 17995-18073 | Clues won't generate |
| Game state | guess_who.js | 1-40 | Game logic issues |
| Category screen | guess_who.js | 100-140 | Category display broken |
| Wake word detection | guess_who.js | 300-380 | Speech recognition fails |
| Guess capture | guess_who.js | 380-430 | Can't capture speech |
| HTML structure | guess_who.html | 1-50 | Page layout broken |
| Button styling | guess_who.html | 50-150 | Buttons too big/small |
| Navigation | gridpage.js | 1787-1800 | Can't access Guess Who |

---

## 🚀 Starting the Test

### Step 1: Verify Setup
```bash
cd /Users/blakethomas/Documents/BravoGCPCopilot
./check_guess_who_setup.sh
# Should see: "✅ All checks passed! Ready for testing."
```

### Step 2: Start Server
```bash
python3 server.py
# Terminal shows: INFO: Uvicorn running on http://127.0.0.1:8000
```

### Step 3: Open Game
1. Browser: http://localhost:8000/gridpage.html
2. Login with test account
3. Navigate to Guess Who

### Step 4: Test & Document
1. Follow testing guide (Quick, Full, or Detailed)
2. Keep DevTools open (F12)
3. Note any RED console errors
4. Document findings

---

## 📊 Documentation Navigation

```
START HERE
    ↓
GUESS_WHO_LOCAL_TEST_COMPLETE.md
    ↓
    ├─ Quick Start? → GUESS_WHO_START_TESTING.md
    │   └─ Got errors? → GUESS_WHO_TESTER_CARD.md (Troubleshooting)
    │
    ├─ Have 2 min? → GUESS_WHO_QUICK_TEST.md
    │   └─ Need more detail? → GUESS_WHO_LOCAL_TEST.md
    │
    ├─ Have 30 min? → GUESS_WHO_LOCAL_TEST.md (Full Test)
    │   └─ Lost? → GUESS_WHO_TESTER_CARD.md (Reference)
    │
    └─ Need setup check? → run check_guess_who_setup.sh
```

---

## ✅ Testing Checklist

- [ ] Read: [GUESS_WHO_LOCAL_TEST_COMPLETE.md](GUESS_WHO_LOCAL_TEST_COMPLETE.md) (overview)
- [ ] Verify: Run `./check_guess_who_setup.sh` (all passes)
- [ ] Review: [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) (setup steps)
- [ ] Start: `python3 server.py` (server running)
- [ ] Open: http://localhost:8000/guess_who.html (game loads)
- [ ] DevTools: Open F12, navigate to Console tab
- [ ] Test: Follow [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md) or [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)
- [ ] Document: Note any RED errors or surprising behavior
- [ ] Reference: Check [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md) for issues
- [ ] Report: Document findings with steps to reproduce

---

## 🎓 Learning Path

### For First-Time Testers
1. [GUESS_WHO_LOCAL_TEST_COMPLETE.md](GUESS_WHO_LOCAL_TEST_COMPLETE.md) - Understand what's there
2. [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) - Learn how to start
3. [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md) - Do quick test
4. [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md) - Keep reference nearby
5. [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) - Do thorough test

### For Experienced Testers
1. [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md) - Refresh quick facts
2. `./check_guess_who_setup.sh` - Verify setup
3. `python3 server.py` - Start server
4. [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) - Run scenarios
5. Document findings

### For Developers
1. [GUESS_WHO_LOCAL_TEST_COMPLETE.md](GUESS_WHO_LOCAL_TEST_COMPLETE.md) - Architecture overview
2. [server.py](server.py) lines 17866-18074 - Backend endpoints
3. [guess_who.js](static/guess_who.js) - Frontend logic
4. [guess_who.html](static/guess_who.html) - UI structure
5. [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) - Test scenarios

---

## 📞 Quick Help

**Q: Where do I start?**
A: [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md) - Step by step setup

**Q: What if something breaks?**
A: [GUESS_WHO_TESTER_CARD.md](GUESS_WHO_TESTER_CARD.md#-common-issues-during-testing) - Quick fixes

**Q: How long will testing take?**
A: 2 min (quick) to 30 min (thorough) - see [GUESS_WHO_QUICK_TEST.md](GUESS_WHO_QUICK_TEST.md)

**Q: What should I look for?**
A: [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md) - 12 test scenarios

**Q: Is everything ready?**
A: Yes! Run `./check_guess_who_setup.sh` to confirm (20/20 checks)

**Q: What are known issues?**
A: [GUESS_WHO_LOCAL_TEST_COMPLETE.md](GUESS_WHO_LOCAL_TEST_COMPLETE.md#-known-issues-documented) - 3 documented issues

---

## 🎮 Game Features You'll Test

✅ **Category Selection**
- Load categories from backend
- Announce selected category
- Proceed to mode selection

✅ **Mode Selection**  
- Choose "You guess" (Mode A implemented)
- Choose "I guess" (Message: "Coming soon")

✅ **Person Selection**
- Generate 6-10 people via LLM
- Display with proper grid layout
- Announce selected person

✅ **Clue Generation**
- Generate 5-6 contextual clues
- Player 1 selects clues to share
- Track clues given (max 3)

✅ **Wake Word Detection**
- Listen for "hey bravo" (configurable)
- Support phonetic variations
- Announce "Listening for your guess"

✅ **Guess Capture**
- Use speech recognition for complete guess
- Display captured guess on screen
- Generate response options via LLM

✅ **Response Selection**
- 6 response options (correct/incorrect)
- Player 1 picks response
- Announce response to user

✅ **Game End Conditions**
- **Win:** Correct guess → Display stats
- **Loss:** Out of guesses → Reveal person

✅ **Navigation**
- Home button from any screen
- Return to gridpage
- Restart game capability

---

## 📝 Sample Test Report

After testing, you can use this template (in [GUESS_WHO_LOCAL_TEST.md](GUESS_WHO_LOCAL_TEST.md)):

```markdown
# Test Report - Guess Who Mode A

Date: [Today's Date]
Tester: [Your Name]
Environment: Local (http://localhost:8000)
Category Tested: Movie Characters
Browser: Chrome 120

## Results Summary
- Categories: ✓
- Mode Selection: ✓
- Person Selection: ✓
- Clue Generation: ✓
- Wake Word Detection: ✓
- Guess Capture: ✓
- Response Options: ✓
- Win Condition: ✓
- Loss Condition: [Test if needed]

## Issues Found
1. [Any console errors? Describe here]
2. [Any unexpected behavior? Describe here]

## Notes
[Observations, suggestions, performance notes]
```

---

## 🚀 Ready to Test?

1. **Setup Check:** `./check_guess_who_setup.sh` ✅ All 20 checks pass
2. **Documentation:** You have 5 comprehensive guides
3. **References:** Quick card for troubleshooting
4. **Code:** All implementation complete and integrated

**Next:** Pick your testing approach and start!

→ [GUESS_WHO_START_TESTING.md](GUESS_WHO_START_TESTING.md)

---

*All documentation prepared and ready for local testing.*  
*Last prepared: 2025*  
*Status: ✅ Ready for Testing*
