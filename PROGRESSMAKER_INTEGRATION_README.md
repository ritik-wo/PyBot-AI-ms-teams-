# ProgressMaker API Integration - Microsoft Teams Bot

## Overview

This implementation integrates your Microsoft Teams bot with the ProgressMaker API to send automated deadline notifications. The system runs daily at 12:00 AM UTC and follows a 3-step API workflow to fetch and deliver deadline cards.

## Key Features

1. **ProgressMaker API Integration**: 3-step authentication workflow
2. **Scheduled Notifications**: Daily at 12:00 AM UTC (configurable)
3. **Fallback to Sample Data**: If API calls fail, uses sample data for testing
4. **User Profile Mapping**: Maps ProgressMaker user IDs to email addresses
5. **Original Card Template**: Uses existing `deadline_template.json` design
6. **Placeholder System**: Shows missing data fields for debugging

## Architecture

### New Components

- **`services/progressmaker_service.py`**: Main ProgressMaker API service
- **`get_token.py`**: Enhanced with ProgressMaker authentication
- **Updated `services/task_service.py`**: Now uses ProgressMaker service
- **Updated `api/message_service.py`**: Maps ProgressMaker data to card template

### Configuration

Update your `.env` file with these new variables:

```env
# Deadline Scheduler Configuration (Updated to 12:00 AM UTC)
DEADLINE_SCHEDULE_HOUR=0
DEADLINE_SCHEDULE_MINUTE=0
DEADLINE_TIMEZONE=UTC

# ProgressMaker API Configuration
PROGRESSMAKER_API_BASE_URL=https://api.test.progressmaker.io
PROGRESSMAKER_API_TIMEOUT=30

# MSAL Configuration for ProgressMaker API
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
TENANT_ID=your_tenant_id_here
MSAL_SCOPE=https://api.test.progressmaker.io/.default
```

## API Workflow

### Step 1: Query Default Context
**Endpoint**: `GET /api/daily/query_default_context`

**Response**:
```json
{
  "executionId": "f7ab23cf-3c3f-4569-b551-78de4beee24a",
  "breakdownId": "90c7adf7-6c25-408d-b6f3-bc6c2e344b86",
  "sprintId": "778d60be-6de9-4c2b-a846-d1691e39d60f"
}
```

### Step 2: Query Organization Profiles
**Endpoint**: `GET /api/profile/organization/query_profiles`

**Response**:
```json
{
  "profiles": [
    {
      "id": "7caf8ce2-45df-4aba-a230-e0ea8fdb929a",
      "email": "alexander.kub@progressmaker.io",
      "userName": null,
      "profileImage": "data:image/jpg;base64,..."
    }
  ]
}
```

### Step 3: Query Progress Items
**Endpoint**: `GET /api/execution/{executionId}/sprint/{sprintId}/query_progress_items`

**Parameters**:
- `dueDate`: Today's date + 2 days (YYYY-MM-DD format)
- `resolved`: false

**Response**: Array of progress items with assignee, due date, etc.

## Data Mapping

### ProgressMaker → Card Template

| ProgressMaker Field | Card Template Field | Notes |
|-------------------|-------------------|-------|
| `description` | Task title | Main task description |
| `progressItemType` | Type badge | agreement/decision/issue |
| `dueDate` | Due date | Formatted as DD.MM. |
| `meetingDate` | Meeting date | Formatted as DD.MM.YYYY |
| `touchPointOrigin.title` | Meeting origin | Source meeting |
| `agendaItem.title` | Agenda item | Related agenda item |
| `itemRelation.name` | Relation | Related target/goal |
| `assignee` | User mapping | Maps to email via profiles |

### Placeholder System

When data is missing, placeholders are shown:
- `[PLACEHOLDER: Missing title]`
- `[PLACEHOLDER: Missing dueDate]`
- `[PLACEHOLDER: Missing email]`
- etc.

This helps identify which fields need attention in your API responses.

## User Workflow

1. **Daily at 12:00 AM UTC**: System starts deadline check
2. **API Authentication**: Gets Bearer token for ProgressMaker API
3. **3-Step API Workflow**:
   - Get execution context
   - Get organization profiles
   - Get progress items (due within 2 days)
4. **User Mapping**: Maps assignee IDs to email addresses
5. **Card Generation**: Uses original template with ProgressMaker data
6. **Teams Delivery**: Sends cards to users via Teams bot
7. **Fallback**: If APIs fail, uses sample data for testing

## Testing

### Manual Testing Endpoints

```bash
# Trigger manual deadline check
curl -X POST http://localhost:3978/api/trigger-deadline-check

# Check scheduler status
curl http://localhost:3978/api/scheduler-status
```

### Sample Data Fallback

The system includes comprehensive sample data that matches the expected API structure. If any API call fails, it automatically falls back to sample data, allowing you to:

1. Test the card template mapping
2. Verify Teams delivery functionality
3. Debug data field requirements
4. Identify missing placeholders

### Expected Sample Data Structure

```json
{
  "id": "112e99d7-f4bb-4c85-984b-ce63810f2414",
  "description": "Strategy current yeah trip tell.",
  "progressItemType": "agreement",
  "assignee": "18ff24be-0668-48d6-85f2-3efc8573958d",
  "dueDate": "2025-12-01",
  "meetingDate": "2025-11-04",
  "touchPointOrigin": {
    "title": "Initiative Monthly: Interior Surfaces"
  },
  "agendaItem": {
    "title": "Introduction"
  },
  "itemRelation": {
    "name": "Optimiert in die Zukunft"
  },
  "resolved": false
}
```

## Authentication

The system uses Microsoft Graph client credentials flow:

1. **Token Acquisition**: Uses `get_token.py` with MSAL
2. **Bearer Authentication**: All API requests include `Authorization: Bearer {token}`
3. **Token Refresh**: Automatic token refresh when needed
4. **Error Handling**: Graceful fallback if authentication fails

## Card Template Preservation

The implementation preserves your existing `deadline_template.json` design:

- ✅ All visual styling maintained
- ✅ Interactive toggles preserved
- ✅ Expandable sections working
- ✅ Icon and badge system intact
- ✅ Column layout unchanged
- ✅ Action buttons functional

Only the text content is dynamically updated with ProgressMaker data.

## Error Handling

### API Failures
- Automatic fallback to sample data
- Detailed logging for debugging
- Graceful degradation

### Missing Data
- Placeholder system shows missing fields
- Cards still render with available data
- Clear error messages in logs

### Authentication Issues
- Retry logic for token acquisition
- Fallback to sample data if auth fails
- Detailed error logging

## Deployment

1. **Update Environment**: Copy `config_example.env` to `.env` and configure
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Configure APIs**: Set up ProgressMaker API credentials
4. **Start Bot**: `python app.py`
5. **Verify Scheduler**: Check logs for "Deadline scheduler started successfully"

## Monitoring

### Logs to Watch
- `[INFO] Deadline scheduler started successfully`
- `🚀 Starting ProgressMaker deadline workflow`
- `✅ Workflow completed. Found X items for Y users`
- `❌ API request failed: {error}` (triggers fallback)

### Success Indicators
- Scheduler shows next run time
- API calls return valid data
- Cards delivered to Teams users
- User interactions processed correctly

## Next Steps

1. **Configure Real APIs**: Replace placeholder credentials with actual ProgressMaker API access
2. **Test Authentication**: Verify Bearer token works with ProgressMaker endpoints
3. **Validate Data Mapping**: Check if all required fields are present in API responses
4. **Monitor Placeholders**: Review cards for any `[PLACEHOLDER: ...]` text
5. **Customize Timing**: Adjust schedule if 12:00 AM UTC doesn't work for your timezone

The system is designed to work immediately with sample data, allowing you to test the complete workflow before connecting to live APIs.
