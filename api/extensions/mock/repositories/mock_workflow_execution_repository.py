"""
Mock implementation of the WorkflowExecutionRepository for performance testing.

This implementation provides no-op write operations and mock read operations,
allowing performance testing of workflow execution without database I/O overhead.
"""

import logging
from typing import Union

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from core.workflow.entities import WorkflowExecution
from core.workflow.repositories.workflow_execution_repository import WorkflowExecutionRepository
from libs.helper import extract_tenant_id
from models import (
    Account,
    CreatorUserRole,
    EndUser,
)
from models.enums import WorkflowRunTriggeredFrom

logger = logging.getLogger(__name__)


class MockWorkflowExecutionRepository(WorkflowExecutionRepository):
    """
    Mock implementation of the WorkflowExecutionRepository interface.

    This implementation is designed for performance testing by:
    - Skipping all write operations (no database I/O)
    - Returning mock data for read operations
    - Maintaining the same interface as production implementations

    Use this to measure the upper performance limit of workflow execution
    without storage overhead.
    """

    def __init__(
        self,
        session_factory: sessionmaker | Engine,
        user: Union[Account, EndUser],
        app_id: str | None,
        triggered_from: WorkflowRunTriggeredFrom | None,
    ):
        """
        Initialize the repository with context information.

        Args:
            session_factory: SQLAlchemy sessionmaker or engine (unused)
            user: Account or EndUser object containing tenant_id, user ID, and role information
            app_id: App ID for filtering by application (can be None)
            triggered_from: Source of the execution trigger (DEBUGGING or APP_RUN)
        """
        logger.info("Mock repository enabled: MockWorkflowExecutionRepository (no data persistence)")
        logger.debug("MockWorkflowExecutionRepository.__init__: app_id=%s, triggered_from=%s", app_id, triggered_from)

        # Extract tenant_id from user
        tenant_id = extract_tenant_id(user)
        if not tenant_id:
            raise ValueError("User must have a tenant_id or current_tenant_id")
        self._tenant_id = tenant_id

        # Store app context
        self._app_id = app_id

        # Extract user context
        self._triggered_from = triggered_from
        self._creator_user_id = user.id

        # Determine user role based on user type
        self._creator_user_role = CreatorUserRole.ACCOUNT if isinstance(user, Account) else CreatorUserRole.END_USER

    def save(self, execution: WorkflowExecution) -> None:
        """
        No-op save operation for performance testing.

        This method intentionally does nothing to eliminate I/O overhead
        during performance testing.

        Args:
            execution: The WorkflowExecution domain entity (ignored)
        """
        logger.debug(
            "MockWorkflowExecutionRepository.save: id=%s, workflow_id=%s, status=%s (no-op)",
            execution.id_,
            execution.workflow_id,
            execution.status.value,
        )
        # Intentionally do nothing - this is a no-op for performance testing
        pass
