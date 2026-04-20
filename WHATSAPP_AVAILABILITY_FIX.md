# WhatsApp Bot Availability Issue - Fixes Applied

## Problem
The bot was reporting "no available time" even when users were certain slots were available, particularly when specifying time constraints like "На вторник после 17:00" (On Tuesday after 17:00).

Additionally, the bot was trying to interpret vague time references like "later" (позже/пізніше) or "after lunch" (после обеда/після обіду), which caused unreliable filtering of available slots.

## Root Causes Identified

### 1. **AI Extraction Issue**
The AI might not have been reliably extracting BOTH date AND time information from a single user message like "На вторник после 17:00". It may have been focusing on just the date or just the time, but not both.

### 2. **Vague Time References**
The bot was trying to extract vague time preferences like "later", "позже", "after lunch" which are ambiguous and led to incorrect filtering of available slots.

### 3. **Lack of Diagnostic Logging**
There was insufficient logging to debug why slots were not being found, making it impossible to determine:
- Whether the AI was extracting time constraints correctly
- How many slots were found before filtering
- Which filters were being applied

## Fixes Applied

### 1. **Removed Vague Time Reference Support**
- ✅ **REMOVED** `time_preference` extraction from AI
- ✅ AI now ONLY extracts specific times like "17:00", "3pm", etc.
- ✅ Vague words like "later" (позже), "after lunch" (после обеда) are now **IGNORED**
- ✅ Users MUST provide specific times for constraints: "после 17:00" ✓, "позже" ✗

### 2. **Improved AI Prompt** (`whatsapp_bot/ai_handler.py`)
- ✅ Added explicit section "CRITICAL - EXTRACT BOTH DATE AND TIME" with examples
- ✅ Expanded time extraction keywords for Russian, Ukrainian, Spanish, and English
- ✅ Added strict rule: "ONLY extract when user provides a SPECIFIC TIME"
- ✅ Emphasized that AI must extract multiple fields from a single message

**Key additions:**
```
CRITICAL - EXTRACT BOTH DATE AND TIME:
When a message contains BOTH date and time information, you MUST extract BOTH fields!
Examples:
- "На вторник после 17:00" -> date: "2026-04-21" AND time_after: "17:00" (extract BOTH!)
- "На пятницу в 14:00" -> date: "2026-04-23" AND time: "14:00" (extract BOTH!)

CRITICAL: Ignore vague time words without specific times!
- "later" / "позже" / "пізніше" WITHOUT a time = DO NOT EXTRACT
- "after lunch" / "после обеда" WITHOUT a time = DO NOT EXTRACT
- ONLY extract when user provides a SPECIFIC TIME like "17:00", "3pm", etc.
```

### 2. **Enhanced Logging** (`whatsapp_bot/views.py`)
Added comprehensive logging at every step:

- ✅ Log user message and AI extraction result
  ```python
  logger.info(f"📥 User message: '{message}'")
  logger.info(f"🤖 AI extracted: {intent_data}")
  ```

- ✅ Log when time constraints are set
  ```python
  logger.info(f"⏰ Set time_after: {time_after}")
  logger.info(f"⏰ Set time_before: {time_before}")
  ```

- ✅ Log complete conversation state after updates
  ```python
  logger.info(f"📊 Updated conversation state: {state}")
  ```

- ✅ Log today's date and booking date for past date checks
  ```python
  logger.info(f"📅 Today: {today}, Booking date: {booking_date}")
  ```

- ✅ Log slot finding with detailed filtering results
  ```python
  logger.info(f"✅ Found {len(slots)} total slots before time filtering")
  logger.info(f"⏰ After time_after filter ({time_after}): {len(slots)} slots (removed {before_filter - len(slots)})")
  logger.info(f"   Available times: {[s['time'] for s in slots[:5]]}")
  ```

- ✅ Log when no slots found with search criteria
  ```python
  logger.warning(f"❌ NO SLOTS FOUND for {service.name} on {booking_date}")
  logger.warning(f"   Search criteria: time_after={state.get('time_after')}, time_before={state.get('time_before')}")
  ```

### 3. **Improved User-Facing Error Messages**
The "no slots" message now shows what constraints were applied:

Before:
```
😔 Извините, нет доступного времени для Manicura semipermanente 21/04/2026.
Попробовать другую дату?
```

After:
```
😔 Извините, нет доступного времени для Manicura semipermanente 21/04/2026 после 17:00.
Попробовать другую дату или время?
```

### 4. **Updated Example Messages**
The bot's greeting examples now use specific times instead of vague references:

Before (vague):
```
• "Хочу запись завтра в 3pm"
• "Доступность в пятницу"
• "Забронировать на понедельник после обеда"  ← VAGUE!
```

After (specific):
```
• "Хочу запись завтра в 3pm"
• "Доступность в пятницу после 17:00"  ← SPECIFIC TIME!
• "Забронировать на понедельник в 14:00"  ← SPECIFIC TIME!
```

### 5. **Diagnostic Test Script**
Created `test_booking_availability.py` to help diagnose issues in production:

```bash
# Test availability for a specific service and date
python test_booking_availability.py

# Test AI message extraction
python test_booking_availability.py ai "На вторник после 17:00"
```

The script shows:
- Company and service details
- Staff working days and hours
- All available slots before filtering
- Slots after applying time constraints
- AI extraction results

## How to Test

1. **Check the logs** - The enhanced logging will now show exactly what's happening:
   ```bash
   tail -f /var/log/your-app/whatsapp.log  # or wherever your logs are
   ```

2. **Run the diagnostic script** on production:
   ```bash
   cd /home/ubuntu/reserva-ya
   source venv/bin/activate
   
   # Edit the script first to set your company ID
   nano test_booking_availability.py
   # Change: company_id = 6  (or whatever your company ID is)
   
   # Run it
   python test_booking_availability.py
   ```

3. **Test AI extraction** for the problematic messages:
   ```bash
   python test_booking_availability.py ai "На вторник после 17:00"
   python test_booking_availability.py ai "Хочу на вторник на 14:00"
   ```

## What to Look For

### Correct User Messages (Will Work):
✅ "На вторник после 17:00" - Has date AND specific time
✅ "Хочу на вторник в 14:00" - Has date AND specific time  
✅ "В пятницу до 18:00" - Has date AND specific time
✅ "21 апреля после 16:00" - Has date AND specific time

### Incorrect/Vague Messages (Will Be Ignored):
❌ "На вторник позже" - Vague "later" without time
❌ "В пятницу после обеда" - Vague "after lunch" without time
❌ "Как-нибудь вечером" - Vague "sometime evening" without time

When a user sends a message, you should now see in the logs:

```
📥 User message: 'На вторник после 17:00'
🤖 AI extracted: {'intent': 'book', 'date': '2026-04-21', 'time_after': '17:00'}
⏰ Set time_after: 17:00
📊 Updated conversation state: {'language': 'ru', 'service_name': 'Manicura semipermanente', 'date': '2026-04-21', 'time_after': '17:00'}
=== SEARCHING SLOTS ===
Company: ANIMA (ID: 6)
Service: Manicura semipermanente (ID: 15)
Date: 2026-04-21
Time after: 17:00
✅ Found 20 total slots before time filtering
⏰ After time_after filter (17:00): 8 slots (removed 12)
   Available times: ['17:00', '17:30', '18:00', '18:30', '19:00']
```

## Potential Remaining Issues

If the problem persists after these fixes, check:

1. **Staff working days** - Ensure staff are configured to work on Tuesdays (weekday=1)
2. **Working hours** - Ensure company/staff have working hours defined for Tuesday
3. **Existing bookings** - Maybe all slots are actually booked
4. **Time zone** - Ensure server time zone is correct
5. **Service configuration** - Check service duration and time_for_servicing are reasonable

## Next Steps

1. Deploy these changes to production
2. Monitor the logs for the next user interaction
3. Run the diagnostic script to verify availability exists
4. If still having issues, share the log output for further debugging
