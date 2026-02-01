# Intelligent Chat History Management Strategy

## Overview
Transform flat chat history into an intelligent, cost-effective system that captures user preferences, avoids repetition, and reduces LLM token costs.

## Current State (Before)
```python
{
  "timestamp": "2026-01-30T10:30:00Z",
  "question": "",
  "response": "Good morning",
  "id": "abc123"
}
```

**Problems:**
- No semantic understanding
- Can't detect repetition
- Can't extract preferences
- All 50 messages sent to LLM (costly)

## New Structure (After)

### Enhanced Chat Entry
```python
{
  "timestamp": "2026-01-30T10:30:00Z",
  "question": "",
  "response": "Good morning",
  "id": "abc123",
  
  # NEW METADATA FIELDS
  "metadata": {
    "type": "greeting",  # greeting|joke|question_answer|statement|request_help|other
    "category": "social",  # social|personal_info|preference|activity|emotion|other
    "is_repetition": False,
    "similar_to": None,  # ID of similar previous message if repetition detected
    "extracted_info": {
      # For question/answer pairs
      "question_topic": "favorite_food",
      "answer_value": "pizza",
      # For statements
      "assertion_type": "preference",
      "assertion_value": "I like jazz music"
    },
    "age_days": 0  # Auto-calculated: days since message
  }
}
```

### AI-Extracted User Narrative (New Firestore Collection)
```
/accounts/{account_id}/users/{user_id}/info/chat_derived_narrative
```

```python
{
  "last_updated": "2026-01-30T10:00:00Z",
  "source_message_count": 45,  # How many messages analyzed
  "extracted_facts": [
    {
      "fact": "User's favorite food is pizza",
      "source_message_id": "abc123",
      "confidence": "high",
      "category": "preference",
      "first_mentioned": "2026-01-15T14:30:00Z",
      "mention_count": 3
    },
    {
      "fact": "User enjoys jazz music",
      "source_message_id": "def456",
      "confidence": "medium",
      "category": "preference",
      "first_mentioned": "2026-01-20T10:00:00Z",
      "mention_count": 1
    }
  ],
  "narrative_text": "User has expressed a preference for pizza as their favorite food (mentioned 3 times). They enjoy jazz music. They frequently greet others with 'Good morning' and 'Hello'.",
  "recent_greetings": ["Good morning", "Hello", "Hi there"],
  "recent_jokes": ["Why did the chicken cross the road? To get to the other side!"],
  "answered_questions": {
    "favorite_food": "pizza",
    "favorite_music": "jazz",
    "hobby": "reading"
  }
}
```

## Implementation Phases

### Phase 1: Enhanced Structure ✓ (Current)
1. Update chat history data model with metadata
2. Create chat_derived_narrative document structure
3. Update recording endpoint to capture basic metadata

### Phase 2: De-duplication Logic
1. Detect greeting repetition
2. Detect joke repetition
3. Track question/answer pairs
4. Prevent showing repeated options

### Phase 3: AI Extraction (Weekly Job)
1. Review messages older than 7 days
2. Extract user facts/preferences
3. Update chat_derived_narrative
4. Archive/summarize old messages

### Phase 4: Cost Optimization
1. Only send recent 7 days to LLM (not all 50)
2. Send chat_derived_narrative instead of old messages
3. Track token savings

## Token Cost Reduction Strategy

### Before:
```
LLM Context:
- 50 chat messages × 100 tokens avg = 5,000 tokens
- Sent on EVERY request
- Cost: High, repetitive
```

### After:
```
BASE CACHE (stable, cached for 24h):
- Chat-derived narrative: ~500 tokens
- Old messages (>7 days): 0 tokens (summarized in narrative)

DELTA CONTEXT (fresh on each request):
- Recent 10 messages: ~1,000 tokens
- Sent on EVERY request

Token Reduction: 5,000 → 1,500 tokens (70% reduction)
```

## De-duplication Strategy

### Greeting Detection
- Track last 5 greetings used
- Flag if greeting used in last 24 hours
- Suggest variations in LLM prompt

### Joke Detection
- Store hash of joke content
- Track when each joke was told
- Prevent same joke within 7 days

### Question Tracking
- Record answered questions
- Include answers in narrative
- Reference in future responses

## Daily Maintenance Job

```bash
# Run daily at 2 AM
0 2 * * * python3 process_chat_history.py --all-users
```

**Job Tasks:**
1. Identify messages > 7 days old
2. Run AI extraction on batch
3. Update chat_derived_narrative
4. Mark messages as "archived" (keep for reference, exclude from LLM)
5. Generate summary report

## Admin UI Additions

### User Info Page - New Section:
```
┌─────────────────────────────────────────┐
│ 📝 Admin-Input Narrative                │
│ (Editable text field)                    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🤖 AI-Extracted Narrative (from chat)   │
│ (Editable, with source citations)       │
│                                          │
│ • Favorite food: pizza                  │
│   (mentioned 3 times, last: Jan 20)     │
│ • Enjoys jazz music                      │
│   (mentioned once, Jan 15)              │
│                                          │
│ [Refresh from Chat] [Clear All]         │
└─────────────────────────────────────────┘
```

## Success Metrics

1. **Cost Reduction:** 70% fewer tokens in chat history context
2. **Repetition Reduction:** <10% repeated greetings/jokes
3. **Preference Capture:** 80%+ of stated preferences extracted
4. **User Experience:** More personalized, less repetitive options

## Next Steps

- [x] Design complete
- [ ] Implement Phase 1 code changes
- [ ] Test with copied prod user
- [ ] Deploy to dev environment
- [ ] Monitor for 1 week
- [ ] Roll out Phases 2-4
