"""
Mock implementation of the WorkflowNodeExecutionRepository for performance testing.

This implementation provides no-op write operations and mock read operations,
allowing performance testing of workflow node execution without database I/O overhead.
"""

import logging
from collections.abc import Sequence
from typing import Union

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from core.workflow.entities import WorkflowNodeExecution
from core.workflow.repositories.workflow_node_execution_repository import (
    OrderConfig,
    WorkflowNodeExecutionRepository,
)
from libs.helper import extract_tenant_id
from models import (
    Account,
    CreatorUserRole,
    EndUser,
    WorkflowNodeExecutionTriggeredFrom,
)

logger = logging.getLogger(__name__)


class MockWorkflowNodeExecutionRepository(WorkflowNodeExecutionRepository):
    """
    Mock implementation of the WorkflowNodeExecutionRepository interface.

    This implementation is designed for performance testing by:
    - Skipping all write operations (no database I/O)
    - Returning mock data for read operations
    - Maintaining the same interface as production implementations

    Use this to measure the upper performance limit of workflow node execution
    without storage overhead.
    """

    def __init__(
        self,
        session_factory: sessionmaker | Engine,
        user: Union[Account, EndUser],
        app_id: str | None,
        triggered_from: WorkflowNodeExecutionTriggeredFrom | None,
    ):
        """
        Initialize the repository with context information.

        Args:
            session_factory: SQLAlchemy sessionmaker or engine (unused)
            user: Account or EndUser object containing tenant_id, user ID, and role information
            app_id: App ID for filtering by application (can be None)
            triggered_from: Source of the execution trigger (SINGLE_STEP or WORKFLOW_RUN)
        """
        logger.info("Mock repository enabled: MockWorkflowNodeExecutionRepository (no data persistence)")
        logger.debug(
            "MockWorkflowNodeExecutionRepository.__init__: app_id=%s, triggered_from=%s", app_id, triggered_from
        )

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

    def save(self, execution: WorkflowNodeExecution) -> None:
        """
        No-op save operation for performance testing.

        This method intentionally does nothing to eliminate I/O overhead
        during performance testing.

        Args:
            execution: The NodeExecution domain entity (ignored)
        """
        logger.debug(
            "MockWorkflowNodeExecutionRepository.save: id=%s, node_execution_id=%s, status=%s (no-op)",
            execution.id,
            execution.node_execution_id,
            execution.status.value,
        )
        # Intentionally do nothing - this is a no-op for performance testing
        pass

    def save_execution_data(self, execution: WorkflowNodeExecution) -> None:
        """
        No-op save execution data operation for performance testing.

        This method intentionally does nothing to eliminate I/O overhead
        during performance testing.

        Args:
            execution: The NodeExecution instance with data to save (ignored)
        """
        logger.debug(
            "MockWorkflowNodeExecutionRepository.save_execution_data: id=%s, node_execution_id=%s (no-op)",
            execution.id,
            execution.node_execution_id,
        )
        # Intentionally do nothing - this is a no-op for performance testing
        pass

    def get_by_workflow_run(
        self,
        workflow_run_id: str,
        order_config: OrderConfig | None = None,
    ) -> Sequence[WorkflowNodeExecution]:
        """
        Return mock node executions for performance testing.

        This method returns a minimal mock response to satisfy interface requirements
        without actual database queries.

        Args:
            workflow_run_id: The workflow run ID
            order_config: Optional configuration for ordering results (ignored)

        Returns:
            Empty list (mock response)
        """
        logger.debug(
            "MockWorkflowNodeExecutionRepository.get_by_workflow_run: workflow_run_id=%s (mock)",
            workflow_run_id,
        )
        # Return empty list as mock response
        return []
