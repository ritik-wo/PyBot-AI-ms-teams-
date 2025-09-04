# Microsoft Teams Bot - Deadline Notification Workflow

## Overview

This implementation extends your existing Microsoft Teams bot with automated deadline notification functionality. The system runs a daily cron job at 12:00 PM to fetch tasks with upcoming deadlines (within 2 days) and sends interactive Adaptive Cards to assigned users.

## Key Features

1. **Scheduled Notifications**: Daily cron job at 12:00 PM (configurable)
2. **Task Fetching**: Retrieves tasks with deadlines within the next 2 days
3. **Interactive Cards**: Users can mark tasks as completed directly in Teams
4. **Automatic Updates**: Task completion status is updated via PUT API calls
5. **Hybrid Messaging**: Uses Bot Framework with Graph API fallback
6. **Manual Testing**: Endpoints for manual triggering and status checking

## Architecture

### New Components

- **`services/scheduler_service.py`**: APScheduler-based cron job management
- **`services/task_service.py`**: Task fetching and updating with placeholder APIs
- **`services/response_handler.py`**: Handles adaptive card responses
- **`resources/pre-meeting-cards/deadline_simple.json`**: Simple adaptive card template

### Modified Components

- **`app.py`**: Added scheduler initialization and new endpoints
- **`bots/teams_conversation_bot.py`**: Added deadline card response handling
- **`api/message_service.py`**: Added simple deadline card builder
- **`requirements.txt`**: Added APScheduler dependency

## Configuration

Copy `config_example.env` to `.env` and configure:

```env
# Deadline Scheduler Configuration
DEADLINE_SCHEDULE_HOUR=12          # Hour to run daily (24-hour format)
DEADLINE_SCHEDULE_MINUTE=0         # Minute to run daily
DEADLINE_TIMEZONE=UTC              # Timezone for scheduling

# Task API Configuration (Replace with your actual APIs)
TASK_API_BASE_URL=https://api.example.com
TASK_API_KEY=your_api_key_here
TASK_API_TIMEOUT=30
```

## API Integration Points

### 1. Task Fetching API

**Location**: `services/task_service.py` → `_call_task_api()`

**Expected Endpoint**: `GET /tasks/upcoming-deadlines`

**Parameters**:
- `start_date`: ISO date string (today)
- `end_date`: ISO date string (today + 2 days)
- `include_assigned_users`: boolean

**Expected Response**:
```json
[
  {
    "id": "task_001",
    "title": "Complete Q4 Sales Analysis",
    "type": "Agreement",
    "dueDate": "2025-01-06T00:00:00Z",
    "assignedTo": "user@example.com",
    "completed": false,
    "description": "Task description"
  }
]
```

### 2. Task Update API

**Location**: `services/task_service.py` → `update_task_completion()`

**Expected Endpoint**: `PUT /tasks/{task_id}`

**Payload**:
```json
{
  "completed": true,
  "updated_by": "user@example.com",
  "updated_at": "2025-01-05T12:00:00Z"
}
```

## New API Endpoints

### Manual Testing

- **`POST /api/trigger-deadline-check`**: Manually trigger deadline notification process
- **`GET /api/scheduler-status`**: Get current scheduler status and next run time

### Example Usage

```bash
# Trigger manual deadline check
curl -X POST http://localhost:3978/api/trigger-deadline-check

# Check scheduler status
curl http://localhost:3978/api/scheduler-status
```

## User Workflow

1. **Daily at 12:00 PM**: System fetches tasks with deadlines within 2 days
2. **Card Delivery**: Users receive adaptive cards in Teams showing their upcoming tasks
3. **User Interaction**: Users can check/uncheck task completion status
4. **Submit**: Users click "Update Progress" to submit their updates
5. **API Update**: System calls your PUT API to update task completion status
6. **Confirmation**: Users receive confirmation of successful updates

## Data Flow

```
Scheduler (12:00 PM) 
    ↓
Fetch Tasks API 
    ↓
Group by User Email 
    ↓
Build Adaptive Cards 
    ↓
Send to Teams Users 
    ↓
User Responds 
    ↓
Update Tasks API 
    ↓
Confirmation Card
```

## Sample Task Data Structure

The system expects tasks in this format:

```json
{
  "id": "task_001",
  "taskId": "task_001",
  "title": "Task Title",
  "type": "Agreement|Decision|Issue",
  "dueDate": "01.02.",
  "dueDateFull": "2025-02-01T00:00:00Z",
  "assignedTo": "user@example.com",
  "completed": false,
  "description": "Task description",
  "meetingOrigin": "Source meeting",
  "meetingDate": "27.01.2025",
  "agendaItem": "Related agenda item",
  "relation": "Related item"
}
```

## Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   - Copy `config_example.env` to `.env`
   - Update with your API endpoints and credentials

3. **Replace Placeholder APIs**:
   - Update `services/task_service.py` → `_call_task_api()` with your actual API calls
   - Test with sample data first

4. **Start the Bot**:
   ```bash
   python app.py
   ```

The scheduler will automatically start and begin running daily at the configured time.

## Testing

### Manual Testing

1. **Trigger Manual Check**:
   ```bash
   curl -X POST http://localhost:3978/api/trigger-deadline-check
   ```

2. **Check Scheduler Status**:
   ```bash
   curl http://localhost:3978/api/scheduler-status
   ```

3. **Test with Sample Data**: The system includes sample task data for testing when APIs are not available.

### User Testing

1. Ensure a user has interacted with the bot in Teams (to establish conversation reference)
2. Trigger manual deadline check
3. User should receive adaptive card
4. User can interact with checkboxes and submit
5. System should call your update API and send confirmation

## Troubleshooting

### Common Issues

1. **No Cards Sent**: Check that users have interacted with the bot first
2. **API Errors**: Verify your task API endpoints and authentication
3. **Scheduler Not Running**: Check logs for scheduler startup errors
4. **Card Not Displaying**: Verify adaptive card JSON structure

### Logs

The system provides detailed logging:
- `[INFO]`: General information
- `[DEBUG]`: Detailed debugging information
- `[ERROR]`: Error conditions

## Next Steps

1. **Replace Placeholder APIs**: Update `services/task_service.py` with your actual API endpoints
2. **Customize Card Template**: Modify `resources/pre-meeting-cards/deadline_simple.json` for your needs
3. **Add Error Handling**: Enhance error handling for your specific API requirements
4. **Configure Scheduling**: Adjust timing and timezone as needed
5. **Add Monitoring**: Consider adding monitoring for the scheduled jobs

## Security Considerations

- Store API keys in environment variables
- Validate user permissions before sending notifications
- Implement rate limiting for manual triggers
- Log all API calls for audit purposes

The implementation is modular and follows best practices, making it easy to customize and extend for your specific requirements.
