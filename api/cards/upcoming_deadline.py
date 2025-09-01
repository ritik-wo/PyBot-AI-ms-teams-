from __future__ import annotations

from typing import Optional, List, Dict, Any

from api.cards.utils import (
    load_card_by_name,
    get_icon_for_task_type,
)


def load_upcoming_deadline_template() -> Optional[dict]:
    """Load the upcoming_deadline_temple.json template (static header/footer, empty rows container)."""
    return load_card_by_name("upcoming_deadline_temple.json")


def _build_task_row_from_reference(task: dict, details_id: str) -> dict:
    """Create a single row (ColumnSet within a Container) following taskStatus.json layout.
    Adds selectAction to toggle the corresponding details container.
    """
    title = task.get('title', '')
    ttype = task.get('type', '')
    due = task.get('dueDate', '')
    icon_name = get_icon_for_task_type(ttype)
    return {
        "type": "Container",
        "selectAction": {
            "type": "Action.ToggleVisibility",
            "targetElements": [
                {"elementId": details_id}
            ]
        },
        "separator": True,
        "spacing": "Small",
        "items": [
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": 3,
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": str(title),
                                "maxLines": 1,
                                "spacing": "Small",
                                "isSubtle": False,
                                "size": "Small"
                            }
                        ],
                        "verticalContentAlignment": "Center"
                    },
                    {
                        "type": "Column",
                        "width": 2,
                        "items": [
                            {
                                "type": "ColumnSet",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {
                                                "type": "Icon",
                                                "name": icon_name,
                                                "size": "xxSmall",
                                                "spacing": "Small"
                                            }
                                        ]
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": str(ttype),
                                                "wrap": True,
                                                "size": "Small"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                        "verticalContentAlignment": "Center"
                    },
                    {
                        "type": "Column",
                        "width": 2,
                        "items": [
                            {
                                "type": "ColumnSet",
                                "spacing": "None",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": str(due),
                                                "size": "Small"
                                            }
                                        ]
                                    },
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {
                                                "type": "Input.Toggle",
                                                "spacing": "None"
                                            }
                                        ],
                                        "spacing": "None"
                                    },
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {
                                                "type": "Icon",
                                                "name": "info",
                                                "size": "xxSmall"
                                            }
                                        ],
                                        "spacing": "None"
                                    }
                                ]
                            }
                        ],
                        "verticalContentAlignment": "Center"
                    }
                ]
            }
        ]
    }


def _build_task_details_from_reference(task: dict, details_id: str) -> dict:
    """Create a details container mirroring taskStatus.json (emphasis style, labels, icons)."""
    return {
        "type": "Container",
        "style": "emphasis",
        "id": details_id,
        "items": [
            {
                "type": "TextBlock",
                "text": str(task.get('detailsTitle', '')),
                "size": "Medium",
                "weight": "Bolder",
                "spacing": "None"
            },
            {
                "type": "ColumnSet",
                "spacing": "Small",
                "columns": [
                    {
                        "type": "Column",
                        "width": 30,
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "Meeting origin",
                                "size": "Small",
                                "isSubtle": True,
                                "spacing": "None"
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": 65,
                        "items": [
                            {
                                "type": "ColumnSet",
                                "spacing": "Small",
                                "columns": [
                                    {
                                        "type": "Column",
                                        "width": "auto",
                                        "items": [
                                            {"type": "Icon", "name": "Calendar", "size": "xSmall"}
                                        ]
                                    },
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {
                                                "type": "TextBlock",
                                                "text": str(task.get('meetingOrigin', '')),
                                                "size": "Small",
                                                "wrap": True
                                            }
                                        ],
                                        "spacing": "ExtraSmall"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "type": "ColumnSet",
                "spacing": "Small",
                "columns": [
                    {
                        "type": "Column",
                        "width": 30,
                        "items": [
                            {"type": "TextBlock", "text": "Meeting date", "size": "Small", "isSubtle": True}
                        ]
                    },
                    {
                        "type": "Column",
                        "width": 65,
                        "items": [
                            {"type": "TextBlock", "text": str(task.get('meetingDate', '')), "size": "Small"}
                        ]
                    }
                ],
                "separator": True
            },
            {
                "type": "ColumnSet",
                "spacing": "Small",
                "columns": [
                    {
                        "type": "Column",
                        "width": 30,
                        "items": [
                            {"type": "TextBlock", "text": "Agenda item", "size": "Small", "isSubtle": True}
                        ],
                        "verticalContentAlignment": "Top"
                    },
                    {
                        "type": "Column",
                        "width": 65,
                        "items": [
                            {"type": "TextBlock", "text": str(task.get('agendaItem', '')), "size": "Small", "wrap": True}
                        ]
                    }
                ],
                "separator": True
            },
            {
                "type": "ColumnSet",
                "spacing": "Small",
                "columns": [
                    {
                        "type": "Column",
                        "width": 30,
                        "items": [
                            {"type": "TextBlock", "text": "Relation", "size": "Small", "isSubtle": True}
                        ]
                    },
                    {
                        "type": "Column",
                        "width": 65,
                        "items": [
                            {
                                "type": "ColumnSet",
                                "spacing": "Small",
                                "columns": [
                                    {"type": "Column", "width": "auto", "items": [{"type": "Icon", "name": "Target", "size": "xSmall"}]},
                                    {
                                        "type": "Column",
                                        "width": "stretch",
                                        "items": [
                                            {"type": "TextBlock", "text": str(task.get('relation', '')), "size": "Small", "wrap": True, "spacing": "None"}
                                        ],
                                        "spacing": "ExtraSmall"
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "separator": True
            }
        ],
        "separator": True,
        "isVisible": False
    }


def build_upcoming_deadline_card(data: dict) -> Optional[dict]:
    """Build the Upcoming Deadline card dynamically from the template, with:
    - Per-row toggle of its own details
    - Exclusive open (one details at a time)
    - Click-outside-to-close on header/title/table header/footer
    """
    template = load_upcoming_deadline_template()
    if not template:
        print("[ERROR] upcoming_deadline_temple.json template not found")
        return None

    try:
        # Make a working copy
        import copy
        card = copy.deepcopy(template)

        # Find the rows container by id "rowsContainer"
        body = card.get('body', [])
        rows_container = None
        for b in body:
            if isinstance(b, dict) and 'items' in b:
                for itm in b['items']:
                    if isinstance(itm, dict) and itm.get('type') == 'Container' and itm.get('id') == 'rowsContainer':
                        rows_container = itm
                        break
            if rows_container:
                break
        if rows_container is None:
            print("[ERROR] rowsContainer not found in upcoming_deadline_temple.json")
            return None

        # Build rows + details
        tasks = data.get('tasks') or []
        rows_and_details: List[Dict[str, Any]] = []
        details_ids: List[str] = []
        for idx, t in enumerate(tasks, start=1):
            did = f"details{idx}"
            details_ids.append(did)
            rows_and_details.append(_build_task_row_from_reference(t, did))
            rows_and_details.append(_build_task_details_from_reference(t, did))
        rows_container['items'] = rows_and_details

        # Enforce exclusive-open: each row sets its details true and others false
        if details_ids:
            for r_index, did in enumerate(details_ids):
                item_index = r_index * 2  # row index in rows_and_details
                if 0 <= item_index < len(rows_and_details):
                    row = rows_and_details[item_index]
                    if isinstance(row, dict):
                        targets = []
                        for other in details_ids:
                            targets.append({
                                "elementId": other,
                                **({"isVisible": True} if other == did else {"isVisible": False})
                            })
                        if 'selectAction' not in row or not isinstance(row['selectAction'], dict):
                            row['selectAction'] = {"type": "Action.ToggleVisibility"}
                        row['selectAction']['type'] = "Action.ToggleVisibility"
                        row['selectAction']['targetElements'] = targets

        # Click outside to close (add ToggleVisibility on non-row areas)
        def _make_close_action(ids: List[str]) -> dict:
            return {
                "type": "Action.ToggleVisibility",
                "targetElements": [{"elementId": i, "isVisible": False} for i in ids]
            }

        if details_ids:
            # Header
            header = body[0] if len(body) > 0 and isinstance(body[0], dict) else None
            if header is not None:
                header["selectAction"] = _make_close_action(details_ids)
            # Meeting title container
            meeting_title = body[1] if len(body) > 1 and isinstance(body[1], dict) else None
            if meeting_title is not None:
                meeting_title["selectAction"] = _make_close_action(details_ids)
            # Table header ColumnSet: body[2] -> items[0]
            if len(body) > 2 and isinstance(body[2], dict):
                table_wrapper = body[2]
                items = table_wrapper.get("items")
                if isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
                    items[0]["selectAction"] = _make_close_action(details_ids)
            # Footer container is last element
            footer = body[-1] if body and isinstance(body[-1], dict) else None
            if footer is not None:
                footer["selectAction"] = _make_close_action(details_ids)

        return card

    except Exception as e:
        print(f"[ERROR] Failed to build upcoming deadline card: {e}")
        return None
