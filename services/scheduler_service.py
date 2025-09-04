# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os

from services.progressmaker_service import ProgressMakerService
from api.messaging_core import send_deadline_to_user_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeadlineSchedulerService:
    """Service to handle scheduled deadline notifications for Microsoft Teams bot"""
    
    def __init__(self, adapter, app_id: str):
        self.scheduler = AsyncIOScheduler()
        self.adapter = adapter
        self.app_id = app_id
        self.is_running = False
        
        # Initialize ProgressMaker service
        self.progressmaker_service = ProgressMakerService()
        
        # Default schedule: 9:00 AM UTC (can be configured)
        self.schedule_hour = int(os.getenv('DEADLINE_SCHEDULE_HOUR', '9'))
        self.schedule_minute = int(os.getenv('DEADLINE_SCHEDULE_MINUTE', '0'))
        self.timezone = os.getenv('DEADLINE_SCHEDULE_TIMEZONE', 'UTC')  # Default UTC
        
    async def start_scheduler(self):
        """Start the deadline notification scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        try:
            # Add the daily job
            self.scheduler.add_job(
                self._process_daily_deadline_notifications,
                CronTrigger(
                    hour=self.schedule_hour,
                    minute=self.schedule_minute,
                    timezone=self.timezone
                ),
                id='daily_deadline_notifications',
                name='Daily Deadline Notifications',
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Deadline scheduler started - will run daily at {self.schedule_hour:02d}:{self.schedule_minute:02d} {self.timezone}")
            
        except Exception as e:
            logger.error(f"Failed to start deadline scheduler: {e}")
            raise
    
    async def stop_scheduler(self):
        """Stop the deadline notification scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
            
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Deadline scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop deadline scheduler: {e}")
            raise
    
    async def _process_daily_deadline_notifications(self):
        """Main job function that runs daily to process deadline notifications"""
        logger.info("=== Starting daily deadline notification process ===")
        
        try:
            # Get deadline workflow data from ProgressMaker service
            # This will try API first, then fallback to sample data if API fails
            workflow_data = await self.progressmaker_service.get_deadline_workflow_data()
            
            grouped_items = workflow_data.get("grouped_items", {})
            
            if not grouped_items:
                logger.info("No upcoming deadline items found")
                return
            
            logger.info(f"Found deadline items for {len(grouped_items)} users")
            
            # Send notifications to each user
            notification_results = []
            for assignee_id, user_data in grouped_items.items():
                try:
                    user_profile = user_data["user_profile"]
                    progress_items = user_data["progress_items"]
                    user_email = user_profile.get("email")
                    
                    if not user_email:
                        logger.warning(f"No email found for user {assignee_id}, skipping")
                        continue
                    
                    logger.info(f"Sending deadline notification to {user_email} for {len(progress_items)} items")
                    
                    # Prepare data for the deadline card using ProgressMaker format
                    card_data = self._prepare_deadline_card_data_from_progressmaker(progress_items, user_profile)
                    
                    # Send the deadline notification
                    result = await send_deadline_to_user_service(
                        email=user_email,
                        adapter=self.adapter,
                        app_id=self.app_id,
                        data_source=card_data
                    )
                    
                    notification_results.append({
                        "user_email": user_email,
                        "item_count": len(progress_items),
                        "status": "success",
                        "result": result
                    })
                    
                    logger.info(f"Successfully sent deadline notification to {user_email}")
                    
                except Exception as e:
                    logger.error(f"Failed to send deadline notification to {user_email}: {e}")
                    notification_results.append({
                        "user_email": user_email,
                        "item_count": len(progress_items) if 'progress_items' in locals() else 0,
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Log summary
            successful = len([r for r in notification_results if r["status"] == "success"])
            failed = len([r for r in notification_results if r["status"] == "failed"])
            
            logger.info(f"=== Daily deadline notification process completed ===")
            logger.info(f"Total users processed: {len(notification_results)}")
            logger.info(f"Successful notifications: {successful}")
            logger.info(f"Failed notifications: {failed}")
            
            if failed > 0:
                failed_users = [r["user_email"] for r in notification_results if r["status"] == "failed"]
                logger.warning(f"Failed to notify users: {', '.join(failed_users)}")
                
        except Exception as e:
            logger.error(f"Daily deadline notification process failed: {e}")
            raise
    
    def _prepare_deadline_card_data_from_progressmaker(self, progress_items: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ProgressMaker data format to deadline card format"""
        # Transform ProgressMaker progress items to the format expected by deadline cards
        tasks = []
        
        for item in progress_items:
            # Map ProgressMaker fields to deadline card expected fields
            task = {
                "taskId": item.get("id"),
                "title": item.get("description", "Unknown Task"),
                "type": item.get("progressItemType", "agreement"),
                "dueDate": item.get("dueDate"),
                "meetingDate": item.get("meetingDate"),
                "completed": item.get("resolved", False),
                "assignedTo": user_profile.get("email"),
                
                # Additional fields from ProgressMaker
                "meetingOrigin": item.get("touchPointOrigin", {}).get("title", "Unknown Meeting"),
                "agendaItem": item.get("agendaItem", {}).get("title", "Unknown Agenda"),
                "relation": item.get("itemRelation", {}).get("name", "Unknown Relation"),
                
                # For backward compatibility with existing templates
                "id": item.get("id"),
                "itemId": item.get("itemId")
            }
            tasks.append(task)
        
        return {
            "tasks": tasks,
            "user_profile": user_profile,
            "user_count": 1,
            "total_tasks": len(tasks),
            "notification_date": datetime.now().strftime("%Y-%m-%d"),
            "notification_type": "deadline_reminder"
        }
    
    def _group_tasks_by_user(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group tasks by assigned user email"""
        tasks_by_user = {}
        
        for task in tasks:
            # Extract user email from task
            user_email = task.get('assignedTo') or task.get('assignedToEmail') or task.get('userEmail')
            
            if not user_email:
                logger.warning(f"Task missing user email assignment: {task.get('title', 'Unknown task')}")
                continue
                
            if user_email not in tasks_by_user:
                tasks_by_user[user_email] = []
                
            tasks_by_user[user_email].append(task)
        
        return tasks_by_user
    
    def _prepare_deadline_card_data(self, user_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data structure for the deadline card template"""
        
        # Calculate days until earliest deadline
        earliest_deadline = None
        for task in user_tasks:
            task_deadline = task.get('dueDate')
            if task_deadline:
                try:
                    # Parse deadline (assuming format like "01.02." or ISO date)
                    if isinstance(task_deadline, str):
                        # Handle different date formats
                        if '.' in task_deadline and len(task_deadline.split('.')) >= 2:
                            # Format like "01.02."
                            day, month = task_deadline.split('.')[:2]
                            current_year = datetime.now().year
                            deadline_date = datetime(current_year, int(month), int(day))
                        else:
                            # Try ISO format or other standard formats
                            from dateutil import parser
                            deadline_date = parser.parse(task_deadline)
                    else:
                        deadline_date = task_deadline
                        
                    if earliest_deadline is None or deadline_date < earliest_deadline:
                        earliest_deadline = deadline_date
                        
                except Exception as e:
                    logger.warning(f"Could not parse deadline date '{task_deadline}': {e}")
        
        # Calculate days left
        days_left = "2 days left"  # Default
        if earliest_deadline:
            delta = earliest_deadline - datetime.now()
            days = delta.days
            if days == 0:
                days_left = "Due today"
            elif days == 1:
                days_left = "1 day left"
            else:
                days_left = f"{days} days left"
        
        # Prepare card data structure compatible with existing template
        card_data = {
            "dueDate": days_left,
            "meeting": {
                "type": user_tasks[0].get('meetingType', 'Progress Review')
            },
            "tasks": []
        }
        
        # Convert tasks to the expected format
        for i, task in enumerate(user_tasks):
            formatted_task = {
                "title": task.get('title', 'Untitled Task'),
                "type": task.get('type', 'Agreement'),
                "dueDate": task.get('dueDate', ''),
                "detailsTitle": f"Details{i+1}",
                "meetingOrigin": task.get('meetingOrigin', 'Automated Deadline Notification'),
                "meetingDate": task.get('meetingDate', datetime.now().strftime('%d.%m.%Y')),
                "agendaItem": task.get('agendaItem', task.get('description', 'Progress item review')),
                "relation": task.get('relation', task.get('title', 'Related task')),
                "taskId": task.get('id') or task.get('taskId'),  # Include task ID for updates
                "completed": task.get('completed', False),
                "assignedTo": task.get('assignedTo') or task.get('assignedToEmail')
            }
            card_data["tasks"].append(formatted_task)
        
        return card_data
    
    async def trigger_manual_notification_check(self) -> Dict[str, Any]:
        """Manually trigger the deadline notification process for testing"""
        logger.info("Manual deadline notification check triggered")
        
        try:
            await self._process_daily_deadline_notifications()
            return {"status": "success", "message": "Manual notification check completed"}
        except Exception as e:
            logger.error(f"Manual notification check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and configuration"""
        next_run = None
        if self.is_running and self.scheduler.get_job('daily_deadline_notifications'):
            next_run_time = self.scheduler.get_job('daily_deadline_notifications').next_run_time
            if next_run_time:
                next_run = next_run_time.isoformat()
        
        return {
            "is_running": self.is_running,
            "schedule_time": f"{self.schedule_hour:02d}:{self.schedule_minute:02d}",
            "timezone": self.timezone,
            "next_run": next_run,
            "job_count": len(self.scheduler.get_jobs()) if self.is_running else 0
        }
