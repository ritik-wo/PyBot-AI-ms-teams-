# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import asyncio
import logging
from typing import Dict, Any, List
from botbuilder.core import TurnContext, MessageFactory, CardFactory
from services.task_service import update_task_completion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeadlineResponseHandler:
    """Handler for processing adaptive card responses from deadline notifications"""
    
    def __init__(self):
        pass
    
    async def handle_deadline_card_response(self, turn_context: TurnContext) -> bool:
        """
        Handle responses from deadline notification adaptive cards.
        
        Args:
            turn_context: The bot turn context containing the response data
            
        Returns:
            bool: True if the response was handled, False otherwise
        """
        try:
            # Check if this is a deadline card response
            if not hasattr(turn_context.activity, 'value') or not turn_context.activity.value:
                return False
            
            action_data = turn_context.activity.value
            
            # Check if this is our deadline notification response
            if action_data.get('action') != 'update_deadline_tasks':
                return False
            
            logger.info(f"Processing deadline card response from user: {turn_context.activity.from_property.name}")
            
            # Extract user information
            user_email = turn_context.activity.from_property.name  # This might need adjustment based on your setup
            user_id = turn_context.activity.from_property.id
            
            # Process task updates
            task_updates = self._extract_task_updates(action_data)
            
            if not task_updates:
                await turn_context.send_activity("No task updates found in your response.")
                return True
            
            # Update tasks
            update_results = await self._process_task_updates(task_updates, user_email)
            
            # Send confirmation response
            await self._send_update_confirmation(turn_context, update_results)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling deadline card response: {e}")
            await turn_context.send_activity("Sorry, there was an error processing your task updates. Please try again.")
            return False
    
    def _extract_task_updates(self, action_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract task update information from the adaptive card response.
        
        Args:
            action_data: The data from the adaptive card submission
            
        Returns:
            List of task updates with task_id and completed status
        """
        task_updates = []
        
        try:
            # Look for toggle inputs in the format "task_{index}_completed"
            for key, value in action_data.items():
                if key.startswith('task_') and key.endswith('_completed'):
                    # Extract task index
                    parts = key.split('_')
                    if len(parts) >= 3:
                        try:
                            task_index = int(parts[1])
                            is_completed = bool(value)
                            
                            # Try to find the corresponding task ID
                            # This assumes task IDs are stored in the action data or can be derived
                            task_id = action_data.get(f'task_{task_index}_id')
                            
                            if not task_id:
                                # Fallback: look for task IDs in a tasks array
                                tasks = action_data.get('tasks', [])
                                if task_index < len(tasks):
                                    task_id = tasks[task_index].get('id') or tasks[task_index].get('taskId')
                            
                            if task_id:
                                task_updates.append({
                                    'task_id': task_id,
                                    'completed': is_completed,
                                    'task_index': task_index
                                })
                            else:
                                logger.warning(f"Could not find task ID for index {task_index}")
                                
                        except ValueError:
                            logger.warning(f"Invalid task index in key: {key}")
            
            logger.info(f"Extracted {len(task_updates)} task updates")
            return task_updates
            
        except Exception as e:
            logger.error(f"Error extracting task updates: {e}")
            return []
    
    async def _process_task_updates(self, task_updates: List[Dict[str, Any]], user_email: str) -> List[Dict[str, Any]]:
        """
        Process the task updates by calling the task update API.
        
        Args:
            task_updates: List of task updates to process
            user_email: Email of the user making the updates
            
        Returns:
            List of update results
        """
        update_results = []
        
        for task_update in task_updates:
            try:
                task_id = task_update['task_id']
                completed = task_update['completed']
                
                logger.info(f"Updating task {task_id} to completed={completed} for user {user_email}")
                
                # Call the task service to update the task
                result = await update_task_completion(task_id, completed, user_email)
                
                update_results.append({
                    'task_id': task_id,
                    'completed': completed,
                    'result': result,
                    'success': result.get('status') == 'success'
                })
                
            except Exception as e:
                logger.error(f"Failed to update task {task_update.get('task_id', 'unknown')}: {e}")
                update_results.append({
                    'task_id': task_update.get('task_id', 'unknown'),
                    'completed': task_update.get('completed', False),
                    'result': {'status': 'error', 'error': str(e)},
                    'success': False
                })
        
        return update_results
    
    async def _send_update_confirmation(self, turn_context: TurnContext, update_results: List[Dict[str, Any]]):
        """
        Send a confirmation message to the user about the task updates.
        
        Args:
            turn_context: The bot turn context
            update_results: Results of the task updates
        """
        successful_updates = [r for r in update_results if r['success']]
        failed_updates = [r for r in update_results if not r['success']]
        
        # Create confirmation card
        confirmation_card = self._create_confirmation_card(successful_updates, failed_updates)
        
        # Send the confirmation
        confirmation_activity = MessageFactory.attachment(CardFactory.adaptive_card(confirmation_card))
        await turn_context.send_activity(confirmation_activity)
    
    def _create_confirmation_card(self, successful_updates: List[Dict[str, Any]], failed_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a confirmation adaptive card showing the update results.
        
        Args:
            successful_updates: List of successful task updates
            failed_updates: List of failed task updates
            
        Returns:
            Adaptive card dictionary
        """
        body_items = [
            {
                "type": "TextBlock",
                "text": "Task Update Confirmation",
                "size": "Large",
                "weight": "Bolder",
                "color": "Default"
            }
        ]
        
        if successful_updates:
            body_items.append({
                "type": "TextBlock",
                "text": f"✅ Successfully updated {len(successful_updates)} task(s)",
                "color": "Good",
                "weight": "Bolder",
                "spacing": "Medium"
            })
            
            # Add details for successful updates
            for update in successful_updates:
                status_text = "Completed" if update['completed'] else "Not completed"
                body_items.append({
                    "type": "TextBlock",
                    "text": f"• Task {update['task_id']}: {status_text}",
                    "size": "Small",
                    "spacing": "Small"
                })
        
        if failed_updates:
            body_items.append({
                "type": "TextBlock",
                "text": f"❌ Failed to update {len(failed_updates)} task(s)",
                "color": "Attention",
                "weight": "Bolder",
                "spacing": "Medium"
            })
            
            # Add details for failed updates
            for update in failed_updates:
                error_msg = update['result'].get('error', 'Unknown error')
                body_items.append({
                    "type": "TextBlock",
                    "text": f"• Task {update['task_id']}: {error_msg}",
                    "size": "Small",
                    "spacing": "Small",
                    "color": "Attention"
                })
        
        # Add timestamp
        from datetime import datetime
        body_items.append({
            "type": "TextBlock",
            "text": f"Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "size": "Small",
            "isSubtle": True,
            "spacing": "Medium"
        })
        
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": body_items
        }


# Global instance for easy import
deadline_response_handler = DeadlineResponseHandler()

# Convenience function for backward compatibility
async def handle_deadline_card_response(turn_context: TurnContext) -> bool:
    """Handle deadline card response"""
    return await deadline_response_handler.handle_deadline_card_response(turn_context)
