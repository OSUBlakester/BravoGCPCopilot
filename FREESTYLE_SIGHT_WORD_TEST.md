# Freestyle Sight Word Testing Instructions

## 🔧 **Issue Found & Fixed**

**Problem**: The main freestyle page was filtering out sight words like "can", "the", "it" as "filler words" before checking if they were sight words, so the sight word detection never worked.

**Solution**: Added sight word check BEFORE the text optimization, using the original word text.

## Quick Test Steps

### 1. Enable Pictograms and Set Sight Word Level
1. Go to: https://dev.talkwithbravo.com/static/admin_settings.html
2. Check "Enable AAC Pictograms" ✅
3. Set "Sight Words Grade Level" to "Kindergarten" or higher
4. Click "Save Settings"

### 2. Test Freestyle Page
1. Go to: https://dev.talkwithbravo.com/static/freestyle.html
2. Open browser console (F12 → Console tab)
3. Look for sight word debug messages like:
   - `🔤 Updated sight word settings: kindergarten`
   - `🔤 Sight word service settings loaded`

### 3. Test Word Options
1. In freestyle page, type some letters to get word suggestions
2. Look for common sight words like: "the", "and", "I", "you", "go", "see", "can"
3. These should appear as **text-only buttons** (no pictures)
4. Non-sight words should show pictograms/images

### 4. Check Console Logs
When sight words are detected, you should see console messages like:
```
🔤 Main freestyle sight word detected: "can" - using text-only display
🔤 Sight word detected: "the" - using text-only display  
🔤 Sight word pictogram blocked: "and" - using text-only display
```

### 5. Test Different Grade Levels
1. Go back to admin settings
2. Try different grade levels:
   - **Pre-Kindergarten**: Only basic words like "the", "I", "go"  
   - **Kindergarten**: More words like "all", "have", "she"
   - **First Grade**: Even more like "after", "could", "when"
3. Refresh freestyle page and test again

## Expected Results

### ✅ Sight Words (should be text-only):
- Pre-K: the, I, and, go, see, you, it, is, can, me, my, we, up, to
- Kindergarten: all, have, she, he, they, what, with, was, are, say
- First Grade: after, could, when, from, had, has, how, just, know

### 🖼️ Non-Sight Words (should show pictograms):
- elephant, computer, dinosaur, pizza, car, house, tree, flower

## Troubleshooting

If sight words are still showing pictograms:

1. **Check Console for Errors**: Look for JavaScript errors in console
2. **Verify Service Loading**: Should see "Sight Word Service initialized" message
3. **Test Service Manually**: In console, try:
   ```javascript
   window.isSightWord("the")  // Should return: true
   window.isSightWord("elephant")  // Should return: false
   ```
4. **Check Settings**: Verify pictograms are enabled and grade level is set
5. **Hard Refresh**: Try Ctrl+F5 to clear cache

## Debug Commands

In browser console, try these commands:

```javascript
// Test sight word service
window.isSightWord("the")
window.isSightWord("elephant") 

// Get current grade level info
window.getSightWordInfo()

// Get all sight words for current level
window.globalSightWordService.getAllSightWords()

// Check if pictograms are enabled
enablePictograms
```

## What Should Happen

1. **Sight words** → Text-only buttons (clean, simple text)
2. **Non-sight words** → Pictogram/image buttons (visual symbols)
3. **Console logs** → Debug messages showing sight word detection
4. **Grade level changes** → Immediate effect on which words are text-only

The key improvement is that the system now checks for sight words in the `getSymbolImageForText()` function, which is called BEFORE the pictogram system, ensuring sight words never get images or pictograms attached to them.