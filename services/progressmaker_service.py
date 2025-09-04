"""ProgressMaker API service for Microsoft Teams bot deadline notifications."""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from get_token import get_graph_token_client_credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProgressMakerService:
    """Service to handle ProgressMaker API calls with authentication and fallback to sample data"""
    
    def __init__(self):
        self.base_url = os.environ.get("PROGRESSMAKER_API_BASE_URL", "https://api.test.progressmaker.io")
        self.timeout = int(os.environ.get("PROGRESSMAKER_API_TIMEOUT", "30"))
        self._access_token = None
        
    async def get_access_token(self) -> str:
        """Get or refresh the access token for ProgressMaker API"""
        try:
            if not self._access_token:
                logger.info("Getting fresh access token for ProgressMaker API")
                self._access_token = get_graph_token_client_credentials()
                logger.info("✅ Access token obtained successfully")
            return self._access_token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise
    
    async def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to ProgressMaker API with fallback"""
        try:
            token = await self.get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}{endpoint}"
            logger.info(f"Making API request to: {url}")
            
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            logger.info(f"✅ API request successful: {response.status_code}")
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ API request failed: {e}")
            return None
    
    async def query_default_context(self) -> Dict[str, Any]:
        """Step 1: Query default context"""
        logger.info("Step 1: Querying default context")
        
        result = await self._make_api_request("/api/daily/query_default_context")
        
        if result:
            return result
        
        # Fallback to sample data
        logger.warning("Using sample data for default context")
        return {
            "executionId": "f7ab23cf-3c3f-4569-b551-78de4beee24a",
            "breakdownId": "90c7adf7-6c25-408d-b6f3-bc6c2e344b86",
            "sprintId": "778d60be-6de9-4c2b-a846-d1691e39d60f"
        }
    
    async def query_organization_profiles(self) -> List[Dict[str, Any]]:
        """Step 2: Query organization profiles"""
        logger.info("Step 2: Querying organization profiles")
        
        result = await self._make_api_request("/api/profile/organization/query_profiles")
        
        if result and "profiles" in result:
            return result["profiles"]
        
        # Fallback to sample data
        logger.warning("Using sample data for organization profiles")
        return [
            {
                "id": "7caf8ce2-45df-4aba-a230-e0ea8fdb929a",
                "email": "alexander.kub@progressmaker.io",
                "userName": None,
                "profileImage": "data:image/jpg;base64,AAngEGAAMAAAABAAIAA"
            },
            {
                "id": "18ff24be-0668-48d6-85f2-3efc8573958d",
                "email": "sample.user@progressmaker.io",
                "userName": "Sample User",
                "profileImage": None
            }
        ]
    
    async def query_progress_items(self, execution_id: str, sprint_id: str, due_date: str) -> List[Dict[str, Any]]:
        """Step 3: Query progress items due within next 2 days"""
        logger.info(f"Step 3: Querying progress items for execution {execution_id}, sprint {sprint_id}, due date {due_date}")
        
        endpoint = f"/api/execution/{execution_id}/sprint/{sprint_id}/query_progress_items"
        params = {
            "dueDate": due_date,
            "resolved": "false"
        }
        
        result = await self._make_api_request(endpoint, params)
        
        if result and isinstance(result, list):
            return result
        
        # Fallback to sample data
        logger.warning("Using sample data for progress items")
        return [
            {
                "id": "112e99d7-f4bb-4c85-984b-ce63810f2414",
                "description": "Strategy current yeah trip tell.",
                "progressItemType": "agreement",
                "assignee": "a6a5c4aa-6755-4b3d-ba57-e18ed225e35a",
                "dueDate": "2025-12-01",
                "meetingDate": "2025-11-04",
                "touchPointOrigin": {
                    "id": "fd435567-fe8c-4d58-856b-23653378b36b",
                    "title": "Initiative Monthly: Interior Surfaces",
                    "sprintId": "68322ec8-7c38-4317-b5ea-c6a4d559be8e",
                    "itemId": "05720672-59b6-4f5c-914b-2e358b375698"
                },
                "agendaItem": {
                    "id": "6b550846-a1ef-43f3-a429-0ba98b1d2bcd",
                    "title": "Introduction",
                    "position": 0
                },
                "itemRelation": {
                    "id": "f66b08b2-882a-4c07-baa6-cbc9fdda5140",
                    "name": "Optimiert in die Zukunft",
                    "itemType": "puzzle_piece"
                },
                "resolved": False,
                "itemId": "123e4567-e89b-12d3-a456-426614174000"
            },
            {
                "id": "223e99d7-f4bb-4c85-984b-ce63810f2415",
                "description": "Complete Q4 Sales Analysis Report",
                "progressItemType": "decision",
                "assignee": "cdc82f24-a55a-43ad-a580-86009a2c31e2",
                "dueDate": "2025-09-06",
                "meetingDate": "2025-09-01",
                "touchPointOrigin": {
                    "id": "fd435567-fe8c-4d58-856b-23653378b36b",
                    "title": "Sales Department Weekly Review",
                    "sprintId": "68322ec8-7c38-4317-b5ea-c6a4d559be8e",
                    "itemId": "05720672-59b6-4f5c-914b-2e358b375699"
                },
                "agendaItem": {
                    "id": "6b550846-a1ef-43f3-a429-0ba98b1d2bce",
                    "title": "Sales Performance Review",
                    "position": 1
                },
                "itemRelation": {
                    "id": "f66b08b2-882a-4c07-baa6-cbc9fdda5141",
                    "name": "Q4 Sales Strategy",
                    "itemType": "target"
                },
                "resolved": False,
                "itemId": "123e4567-e89b-12d3-a456-426614174001"
            }
        ]
    
    async def get_deadline_workflow_data(self) -> Dict[str, Any]:
        """Execute the complete 3-step workflow and return processed data"""
        logger.info("🚀 Starting ProgressMaker deadline workflow")
        
        try:
            # Step 1: Get default context
            context = await self.query_default_context()
            execution_id = context.get("executionId")
            sprint_id = context.get("sprintId")
            
            if not execution_id or not sprint_id:
                raise ValueError("Missing executionId or sprintId from default context")
            
            # Step 2: Get organization profiles for user mapping
            profiles = await self.query_organization_profiles()
            
            # Create user ID to profile mapping
            user_profiles = {profile["id"]: profile for profile in profiles}
            
            # Step 3: Get progress items (due date = today + 2 days)
            today = datetime.now().date()
            due_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
            
            progress_items = await self.query_progress_items(execution_id, sprint_id, due_date)
            
            # Group progress items by assignee and get real user emails
            grouped_items = {}
            for item in progress_items:
                assignee_id = item.get("assignee")
                if assignee_id:
                    if assignee_id not in grouped_items:
                        # Try to get user profile from ProgressMaker data first
                        user_profile = user_profiles.get(assignee_id)
                        
                        # If not found in ProgressMaker profiles, try to get from Microsoft Graph
                        if not user_profile:
                            user_profile = await self._get_user_profile_from_graph(assignee_id)
                        
                        # If still not found, use placeholder
                        if not user_profile:
                            user_profile = {
                                "id": assignee_id,
                                "email": f"user-{assignee_id}@placeholder.com",
                                "userName": f"User {assignee_id[:8]}",
                                "profileImage": None
                            }
                        
                        grouped_items[assignee_id] = {
                            "user_profile": user_profile,
                            "progress_items": []
                        }
                    grouped_items[assignee_id]["progress_items"].append(item)
            
            logger.info(f"✅ Workflow completed. Found {len(progress_items)} items for {len(grouped_items)} users")
            
            return {
                "context": context,
                "grouped_items": grouped_items,
                "total_items": len(progress_items),
                "total_users": len(grouped_items)
            }
            
        except Exception as e:
            logger.error(f"❌ Workflow failed: {e}")
            raise
    
    async def _get_user_profile_from_graph(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from Microsoft Graph API using user ID"""
        try:
            from api.graph_api import get_fresh_graph_access_token
            
            # Get Graph API access token
            access_token = get_fresh_graph_access_token()
            
            # Try to get user by ID
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            logger.info(f"[DEBUG] Looking up user by ID: {user_id}")
            response = requests.get(url, headers=headers)
            logger.info(f"[DEBUG] Graph API response: {response.status_code}")
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"[DEBUG] Found user: {user_data.get('mail', user_data.get('userPrincipalName'))}")
                
                return {
                    "id": user_id,
                    "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                    "userName": user_data.get("displayName"),
                    "profileImage": None
                }
            else:
                logger.warning(f"[DEBUG] User not found in Graph API: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to get user from Graph API: {e}")
            return None


# Async function for backward compatibility
async def fetch_upcoming_deadline_tasks(days_ahead: int = 2) -> List[Dict[str, Any]]:
    """Fetch upcoming deadline tasks using ProgressMaker API"""
    service = ProgressMakerService()
    workflow_data = await service.get_deadline_workflow_data()
    
    # Convert to the expected format for existing code
    tasks = []
    for user_id, user_data in workflow_data["grouped_items"].items():
        user_profile = user_data["user_profile"]
        for item in user_data["progress_items"]:
            # Map ProgressMaker data to expected task format
            task = {
                "id": item.get("id"),
                "taskId": item.get("itemId", item.get("id")),
                "title": item.get("description", "[PLACEHOLDER: Missing description]"),
                "type": item.get("progressItemType", "agreement").title(),
                "dueDate": item.get("dueDate", "[PLACEHOLDER: Missing dueDate]"),
                "dueDateFull": item.get("dueDate", "[PLACEHOLDER: Missing dueDate]"),
                "assignedTo": user_profile.get("email", "[PLACEHOLDER: Missing email]"),
                "assigneeId": user_id,
                "completed": not item.get("resolved", True),
                "description": item.get("description", "[PLACEHOLDER: Missing description]"),
                "meetingOrigin": item.get("touchPointOrigin", {}).get("title", "[PLACEHOLDER: Missing meeting origin]"),
                "meetingDate": item.get("meetingDate", "[PLACEHOLDER: Missing meeting date]"),
                "agendaItem": item.get("agendaItem", {}).get("title", "[PLACEHOLDER: Missing agenda item]"),
                "relation": item.get("itemRelation", {}).get("name", "[PLACEHOLDER: Missing relation]")
            }
            tasks.append(task)
    
    return tasks
