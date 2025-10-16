"""
Actions module for performing external actions like notifications.
"""

from fraim.actions.github import add_code_annotation, add_comment, add_reviewer
from fraim.actions.slack import send_message

__all__ = ["add_comment", "add_reviewer", "add_code_annotation", "send_message"]
