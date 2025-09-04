# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
import os
from dateutil import parser
from services.progressmaker_service import fetch_upcoming_deadline_tasks as pm_fetch_tasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskService:
    """Service to handle task-related operations for deadline notifications"""
    
    def __init__(self):
        # Configuration from environment variables
        self.task_api_base_url = os.environ.get("TASK_API_BASE_URL", "https://api.example.com")
        self.task_api_key = os.environ.get("TASK_API_KEY", "")
        self.task_api_timeout = int(os.environ.get("TASK_API_TIMEOUT", "30"))
        
    async def fetch_upcoming_deadline_tasks(self, days_ahead: int = 2) -> List[Dict[str, Any]]:
        """
        Fetch all tasks whose deadline is within the next specified days using ProgressMaker API.
        
        Args:
            days_ahead: Number of days to look ahead for deadlines
            
        Returns:
            List of task dictionaries with deadline information
        """
        logger.info(f"Fetching tasks with deadlines within the next {days_ahead} days from ProgressMaker API")
        
        try:
            # Use ProgressMaker service to fetch tasks
            tasks = await pm_fetch_tasks(days_ahead)
            
            if not tasks:
                logger.warning("No tasks returned from ProgressMaker API")
                return []
            
            # Filter and validate tasks
            valid_tasks = []
            for task in tasks:
                if self._is_valid_task(task):
                    # Ensure task has required fields
                    processed_task = self._process_task_data(task)
                    valid_tasks.append(processed_task)
                else:
                    logger.warning(f"Invalid task data: {task.get('id', 'unknown')}")
            
            logger.info(f"Successfully processed {len(valid_tasks)} valid tasks")
            return valid_tasks
            
        except Exception as e:
            logger.error(f"Failed to fetch upcoming deadline tasks: {e}")
            # Return sample data for testing if API fails
            return await self._get_sample_deadline_tasks(days_ahead)
    
    async def update_task_completion(self, task_id: str, completed: bool, user_email: str) -> Dict[str, Any]:
        """
        Update the completion status of a specific task.
        
        Args:
            task_id: Unique identifier of the task
            completed: Whether the task is completed
            user_email: Email of the user making the update
            
        Returns:
            Dictionary with update result
        """
        logger.info(f"Updating task {task_id} completion status to {completed} by {user_email}")
        
        try:
            # TODO: Replace this with your actual API call
            result = await self._call_task_api(
                endpoint=f"/tasks/{task_id}",
                method="PUT",
                data={
                    "completed": completed,
                    "updated_by": user_email,
                    "updated_at": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Successfully updated task {task_id}")
            return {
                "status": "success",
                "task_id": task_id,
                "completed": completed,
                "updated_by": user_email,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e)
            }
    
    async def _call_task_api(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None, data: Optional[Dict] = None) -> Any:
        """
        Make API call to the task management system.
        
        This is a placeholder implementation that you should replace with your actual API.
        """
        url = f"{self.task_api_base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.task_api_key}",
            "Content-Type": "application/json"
        }
        
        logger.debug(f"Making {method} request to {url}")
        
        # TODO: Replace this placeholder with your actual API implementation
        if method.upper() == "GET":
            # Simulate API response for GET requests
            if "upcoming-deadlines" in endpoint:
                return await self._get_sample_deadline_tasks()
            else:
                return []
        elif method.upper() == "PUT":
            # Simulate API response for PUT requests
            return {
                "id": data.get("task_id") if data else "unknown",
                "updated": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise NotImplementedError(f"Method {method} not implemented in placeholder")
    
    def _is_valid_task(self, task: Dict[str, Any]) -> bool:
        """Validate that a task has the required fields"""
        required_fields = ['id', 'title', 'dueDate']
        return all(field in task for field in required_fields)
    
    def _process_task_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize task data from the API"""
        processed = task.copy()
        
        # Ensure consistent field names
        if 'assignedTo' not in processed and 'assigned_to' in processed:
            processed['assignedTo'] = processed['assigned_to']
        
        if 'taskId' not in processed and 'id' in processed:
            processed['taskId'] = processed['id']
        
        # Parse and normalize due date
        due_date = processed.get('dueDate')
        if due_date and isinstance(due_date, str):
            try:
                parsed_date = parser.parse(due_date)
                # Format as DD.MM. for compatibility with existing templates
                processed['dueDate'] = parsed_date.strftime('%d.%m.')
                processed['dueDateFull'] = parsed_date.isoformat()
            except Exception as e:
                logger.warning(f"Could not parse due date '{due_date}': {e}")
        
        # Set default values for missing fields
        defaults = {
            'type': 'Agreement',
            'completed': False,
            'meetingType': 'Progress Review',
            'meetingOrigin': 'Automated Deadline Notification',
            'meetingDate': datetime.now().strftime('%d.%m.%Y'),
            'agendaItem': 'Progress item review',
            'relation': processed.get('title', 'Related task')
        }
        
        for key, default_value in defaults.items():
            if key not in processed:
                processed[key] = default_value
        
        return processed
    
    async def _get_sample_deadline_tasks(self, days_ahead: int = 2) -> List[Dict[str, Any]]:
        """
        Return sample task data for testing purposes.
        Replace this with actual API integration.
        """
        logger.info("Using sample deadline tasks data (replace with actual API)")
        
        # Calculate sample due dates
        tomorrow = datetime.now() + timedelta(days=1)
        day_after = datetime.now() + timedelta(days=2)
        
        sample_tasks = [
            {
                "id": "task_001",
                "taskId": "task_001",
                "title": "Complete Q4 Sales Analysis",
                "type": "Agreement",
                "dueDate": tomorrow.strftime('%d.%m.'),
                "dueDateFull": tomorrow.isoformat(),
                "assignedTo": "user@example.com",  # Replace with actual user email
                "assignedToEmail": "user@example.com",
                "completed": False,
                "description": "Analyze Q4 sales performance and prepare recommendations",
                "meetingType": "Sales Review",
                "meetingOrigin": "Q4 Planning Meeting",
                "meetingDate": datetime.now().strftime('%d.%m.%Y'),
                "agendaItem": "Q4 Sales Performance Review and Strategic Planning",
                "relation": "Sales Performance Optimization"
            },
            {
                "id": "task_002", 
                "taskId": "task_002",
                "title": "Update Marketing Campaign Strategy",
                "type": "Decision",
                "dueDate": day_after.strftime('%d.%m.'),
                "dueDateFull": day_after.isoformat(),
                "assignedTo": "marketing@example.com",  # Replace with actual user email
                "assignedToEmail": "marketing@example.com",
                "completed": False,
                "description": "Review and update marketing campaign strategy for next quarter",
                "meetingType": "Marketing Strategy",
                "meetingOrigin": "Marketing Planning Session",
                "meetingDate": datetime.now().strftime('%d.%m.%Y'),
                "agendaItem": "Marketing Campaign Strategy Review",
                "relation": "Campaign Optimization"
            },
            {
                "id": "task_003",
                "taskId": "task_003", 
                "title": "Prepare Budget Proposal",
                "type": "Agreement",
                "dueDate": tomorrow.strftime('%d.%m.'),
                "dueDateFull": tomorrow.isoformat(),
                "assignedTo": "finance@example.com",  # Replace with actual user email
                "assignedToEmail": "finance@example.com",
                "completed": False,
                "description": "Prepare detailed budget proposal for next fiscal year",
                "meetingType": "Budget Planning",
                "meetingOrigin": "Financial Planning Meeting",
                "meetingDate": datetime.now().strftime('%d.%m.%Y'),
                "agendaItem": "Budget Planning and Resource Allocation",
                "relation": "Financial Planning"
            }
        ]
        
        return sample_tasks


# Global instance for easy import
task_service = TaskService()

# Convenience functions for backward compatibility
async def fetch_upcoming_deadline_tasks(days_ahead: int = 2) -> List[Dict[str, Any]]:
    """Fetch tasks with upcoming deadlines"""
    return await task_service.fetch_upcoming_deadline_tasks(days_ahead)

async def update_task_completion(task_id: str, completed: bool, user_email: str) -> Dict[str, Any]:
    """Update task completion status"""
    return await task_service.update_task_completion(task_id, completed, user_email)
