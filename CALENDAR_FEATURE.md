# Calendar Invite Attachments Feature

## Overview

This feature adds downloadable calendar invite (.ics) files to Discord notifications when bookings are successfully confirmed. Users can download the attachment and import it into their calendar application (Google Calendar, Outlook, Apple Calendar, etc.).

## Implementation Details

### New Files

#### `calendar_utils.py`
Calendar generation module with timezone-aware datetime handling.

**Key Components:**
- `CalendarInviteGenerator` class - Main calendar file generator
- `parse_time_to_datetime()` - Converts time strings ("10am", "7pm") to datetime objects
- `generate_ics()` - Creates RFC 5545 compliant .ics files as in-memory BytesIO
- `generate_filename()` - Generates descriptive filenames

**Features:**
- UK timezone support (`Europe/London`) with automatic BST/GMT handling
- 1-hour booking duration (configurable)
- 1-hour reminder alarm
- Event marked as CONFIRMED and OPAQUE (busy time)

### Modified Files

#### `requirements.txt`
Added: `icalendar==6.3.2`

#### `notifications.py`
**Changes to `send_message()`:**
- Added optional `files` parameter for attachments
- Supports multipart/form-data when files are present
- Maintains backward compatibility for existing notifications

**Changes to `booking_success()`:**
- Generates .ics file using `calendar_generator.generate_ics()`
- Attaches file to Discord message
- Adds calendar emoji field to embed
- Graceful fallback: sends notification without attachment if calendar generation fails

## Calendar File Details

### Event Properties

```
Summary:      "Padel Court Booking - [Court Name]"
Description:  Multi-line with date, time, court details
Location:     "Estelle Manor Padel Courts"
Duration:     1 hour (start time + 1hr)
Timezone:     Europe/London (handles BST/GMT automatically)
Status:       CONFIRMED
Transparency: OPAQUE (shows as busy)
Reminder:     1 hour before event
```

### Example Filename
`padel_booking_2026-02-17_10am.ics`

### Example .ics Content

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Padel Court Booking System//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
SUMMARY:Padel Court Booking - Court 1
DTSTART;TZID=Europe/London:20260217T100000
DTEND;TZID=Europe/London:20260217T110000
DTSTAMP:20260202T172238Z
DESCRIPTION:Padel Court Booking Confirmation...
LOCATION:Estelle Manor Padel Courts
STATUS:CONFIRMED
TRANSP:OPAQUE
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Padel Court Booking - Court 1
TRIGGER:-PT1H
END:VALARM
END:VEVENT
END:VCALENDAR
```

## Testing

### Unit Tests

Run the test suite to verify calendar generation:

```bash
docker run --rm gc-estelle:test python test_calendar_simple.py
```

**Tests include:**
- Time parsing for various formats (10am, 7pm, 7:30pm)
- Filename generation
- .ics file structure validation
- Required component verification

### Manual Testing

1. **Test calendar generation:**
   ```bash
   docker run --rm gc-estelle:test python -c "
   from calendar_utils import calendar_generator
   ics = calendar_generator.generate_ics('2026-02-17', '10am', 'Court 1')
   ics.seek(0)
   with open('test.ics', 'wb') as f:
       f.write(ics.read())
   "
   ```

2. **Import test.ics into calendar apps:**
   - Google Calendar
   - Outlook (Desktop/Web)
   - Apple Calendar
   - Verify: date, time, location, reminder

3. **Test Discord integration:**
   - Trigger a successful booking (or use test endpoint)
   - Check Discord for message with attachment
   - Download .ics file
   - Import into personal calendar

## Error Handling

**Graceful Degradation:**
- If calendar generation fails → Logs error, sends notification WITHOUT attachment
- If Discord multipart upload fails → Standard error handling in `send_message()`
- Notifications are NEVER blocked by calendar feature failures

## Deployment

### Local Development

1. Install dependency:
   ```bash
   pip install icalendar==6.3.2
   ```

### Docker Deployment

1. Build new Docker image:
   ```bash
   docker build -t gc-estelle:latest .
   ```

2. The `requirements.txt` includes `icalendar==6.3.2`, so it will be installed automatically

### Control Plane Deployment

The Terraform configuration in `terraform/` handles deployment to Control Plane. After pushing the new Docker image:

```bash
cd terraform
terraform apply
```

Or manually update the deployment via Control Plane UI.

## Integration Flow

```
Booking succeeds (booking_engine.py:401)
    ↓
notifier.booking_success(booking_date, booked_time, court_name)
    ↓
Generate .ics file with calendar_generator
    ↓
Attach file to Discord multipart/form-data request
    ↓
Discord webhook sends message with downloadable .ics attachment
    ↓
User downloads .ics and imports to calendar
```

## Design Decisions

### In-Memory Generation
Files are generated as BytesIO objects (not saved to disk):
- No disk I/O overhead
- No cleanup needed
- More secure
- Simpler code
- Files are small (~600-700 bytes)

### Library Choice: icalendar
Chosen over alternatives for:
- Maturity and wide adoption (~5M downloads/month)
- RFC 5545 compliance
- Excellent timezone support with zoneinfo
- Fine-grained control over event properties
- Production-proven track record

### Timezone Handling
Uses `Europe/London` for UK-based Estelle Manor:
- zoneinfo handles BST/GMT transitions automatically
- Major calendar applications respect TZID property
- No manual offset calculations needed

### Multipart vs JSON
Discord file attachments require multipart/form-data:
- JSON payload goes in `payload_json` field
- File data in `files[0]` field
- httpx handles multipart encoding automatically

## Verification Checklist

After deployment, verify:

- [ ] Discord notification includes .ics file attachment
- [ ] Calendar file imports successfully in Google Calendar
- [ ] Calendar file imports successfully in Outlook
- [ ] Calendar file imports successfully in Apple Calendar
- [ ] Event shows correct date and time with timezone
- [ ] Reminder is set (1 hour before)
- [ ] Location is set correctly
- [ ] Event shows as "busy" time
- [ ] Error fallback works (notification sent even if calendar generation fails)
- [ ] Unit tests pass
- [ ] No errors in application logs

## Troubleshooting

### Calendar file not generated
- Check logs for calendar generation errors
- Verify icalendar package is installed
- Ensure timezone data is available (zoneinfo)

### Discord attachment not appearing
- Check Discord webhook URL is correct
- Verify multipart/form-data is being used
- Check file size is reasonable (<8MB)
- Review Discord API error responses

### Calendar import fails
- Verify .ics file structure with test script
- Check timezone is valid (Europe/London)
- Ensure all required fields are present
- Test with multiple calendar applications

### Wrong time displayed
- Verify timezone handling in parse_time_to_datetime()
- Check calendar app timezone settings
- Ensure TZID property is set correctly

## Future Enhancements

Potential improvements for future iterations:

1. **Configurable duration** - Allow different booking lengths
2. **Custom reminder times** - User-selectable reminder offset
3. **Multiple attendees** - Add other players to event
4. **Recurring events** - Support for regular bookings
5. **Event updates** - Update existing calendar events if booking changes
6. **Custom event colors** - Color-code by court or time
7. **RSVP support** - REQUEST method for confirmation workflow
