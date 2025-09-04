"""
DEPRECATED: This file has been refactored into smaller, more focused modules.

New structure:
- api/card_loaders.py - Template loading functions
- api/deadline_service.py - Deadline-specific card functions  
- api/messaging_core.py - Core messaging logic
- api/card_update_service.py - Card update functionality

This file now serves as a compatibility layer for existing imports.
"""

# Re-export functions from the new modular structure for backward compatibility
from .card_loaders import (
    load_tasks_assigned_card,
    load_card_by_name,
    load_updated_tasks_card,
    load_sample_data,
    load_task_status_template,
    load_deadline_template
)

from .deadline_service import (
    build_deadline_card_simple,
    build_deadline_card_from_sample_exm,
    build_task_status_card,
    get_icon_for_task_type,
    replace_icon_names
)

from .messaging_core import (
    send_message_to_user_service,
    send_deadline_to_user_service,
    send_message_via_bot_framework_with_card,
    send_adaptive_card_to_chat
)

from .card_update_service import (
    update_card_service,
    update_card_via_bot_framework,
    update_card_via_graph_api
)

# Re-export from existing card modules
from api.cards.tasks_assigned import (
    build_dynamic_card_with_tasks,
    extract_task_section_template,
    generate_task_sections,
    inject_task_sections_into_card,
)

from api.cards.utils import (
    populate_placeholders,
)

from api.cards.upcoming_deadline import (
    load_upcoming_deadline_template,
    build_upcoming_deadline_card,
)

# Legacy wrapper functions for backward compatibility
def populate_card_template(template: dict, data: dict) -> dict:
    """Legacy function - kept for backward compatibility"""
    return populate_placeholders(template, data)
