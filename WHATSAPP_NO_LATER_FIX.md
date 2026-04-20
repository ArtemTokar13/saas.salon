# WhatsApp Bot - "Later" Time Reference Fix

## Issue
The bot was incorrectly handling vague time references like:
- "later" / "позже" / "пізніше"
- "after lunch" / "после обеда" / "після обіду"
- "in the evening" / "вечером" / "ввечері" (without specific time)

These vague references were being interpreted as time constraints, causing the bot to filter available slots incorrectly and report "no availability" even when slots existed.

## Solution
**The bot now IGNORES all vague time references completely.**

Users MUST provide specific times:
- ✅ "после 17:00" (after 17:00)
- ✅ "в 14:00" (at 14:00)
- ✅ "до 18:00" (before 18:00)
- ❌ "позже" (later) - IGNORED
- ❌ "после обеда" (after lunch) - IGNORED

## Changes Made

### 1. AI Prompt Updated (`whatsapp_bot/ai_handler.py`)
Removed `time_preference` field completely and added strict rules:

```
DO NOT EXTRACT time_preference field at all! Ignore vague time words like "later", "позже", "пізніше" completely.

CRITICAL: Ignore vague time words without specific times!
- "later" / "позже" / "пізніше" WITHOUT a time = DO NOT EXTRACT
- "after lunch" / "после обеда" WITHOUT a time = DO NOT EXTRACT
- ONLY extract when user provides a SPECIFIC TIME like "17:00", "3pm", etc.
```

### 2. Example Messages Updated (`whatsapp_bot/views.py`)
Changed greeting examples to show correct format:

**Before:**
```python
'ru': ['завтра в 3pm', 'в пятницу', 'в понедельник после обеда'],
```

**After:**
```python
'ru': ['завтра в 3pm', 'в пятницу после 17:00', 'в понедельник в 14:00'],
```

## User Guidance

The bot will now train users to provide specific times by example. When they see:
```
Я могу помочь вам забронировать визит. Например:
• "Хочу запись завтра в 3pm"
• "Доступность в пятницу после 17:00"
• "Забронировать на понедельник в 14:00"
```

They will learn to always include specific times in their requests.

## Why This Matters

**Before (with vague references):**
- User: "На вторник позже"
- Bot extracts: `time_preference: "afternoon"` 
- Bot filters OUT morning slots even though user might want them
- Result: Fewer or no slots shown ❌

**After (specific times only):**
- User: "На вторник после 17:00"
- Bot extracts: `time_after: "17:00"`
- Bot shows ONLY slots after 17:00 as requested
- Result: Accurate availability ✅

**Or if user doesn't specify time:**
- User: "На вторник"
- Bot extracts: No time constraints
- Bot shows ALL available slots on Tuesday
- Result: User sees all options ✅

## Testing

To verify this works:

```bash
cd /home/ubuntu/reserva-ya
source venv/bin/activate

# Test that vague references are ignored
python test_booking_availability.py ai "На вторник позже"
# Should NOT extract time_preference or any time constraint

# Test that specific times are extracted
python test_booking_availability.py ai "На вторник после 17:00"
# Should extract: date: "2026-04-21", time_after: "17:00"
```

Expected output for "позже" (later):
```json
{
  "intent": "book",
  "date": "2026-04-21"
  // NO time_preference, NO time_after, NO time_before
}
```

Expected output for "после 17:00" (after 17:00):
```json
{
  "intent": "book", 
  "date": "2026-04-21",
  "time_after": "17:00"
}
```

## Summary

✅ Vague time words like "later", "позже", "after lunch" are now IGNORED  
✅ Only specific times like "17:00", "14:00", "3pm" are extracted  
✅ Examples in greeting messages updated to show correct format  
✅ Users will be guided to provide specific times  
✅ No more false "no availability" errors from vague time filtering
