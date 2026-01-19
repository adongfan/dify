"""
Mock implementation of the DifyAPIWorkflowNodeExecutionRepository for performance testing.

This implementation provides no-op write operations and mock read operations,
allowing performance testing of workflow node executions without database I/O overhead.
"""

import logging
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from core.workflow.entities import WorkflowNodeExecution
from core.workflow.repositories.workflow_node_execution_repository import (
    OrderConfig,
)
from models.workflow import WorkflowNodeExecutionModel
from repositories.api_workflow_node_execution_repository import DifyAPIWorkflowNodeExecutionRepository

logger = logging.getLogger(__name__)


class MockAPIWorkflowNodeExecutionRepository(DifyAPIWorkflowNodeExecutionRepository):
    """
    Mock implementation of DifyAPIWorkflowNodeExecutionRepository for performance testing.

    This implementation is designed for performance testing by:
    - Skipping all write operations (no database I/O)
    - Returning mock/empty data for read operations
    - Maintaining the same interface as production implementations

    Use this to measure the upper performance limit of workflow node execution
    without storage overhead.
    """

    def __init__(self, session_maker: sessionmaker | None = None):
        """
        Initialize the repository.

        Args:
            session_maker: SQLAlchemy sessionmaker (unused, for compatibility)
        """
        logger.info("Mock repository enabled: MockAPIWorkflowNodeExecutionRepository (no data persistence)")
        logger.debug("MockAPIWorkflowNodeExecutionRepository.__init__: initializing")

    def save(self, execution: WorkflowNodeExecution) -> None:
        """
        No-op save operation for performance testing.

        Args:
            execution: The NodeExecution domain entity (ignored)
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.save: id=%s (no-op)",
            execution.id,
        )
        # Intentionally do nothing - this is a no-op for performance testing
        pass

    def save_execution_data(self, execution: WorkflowNodeExecution) -> None:
        """
        No-op save execution data operation for performance testing.

        Args:
            execution: The NodeExecution instance with data to save (ignored)
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.save_execution_data: id=%s (no-op)",
            execution.id,
        )
        # Intentionally do nothing - this is a no-op for performance testing
        pass

    def get_by_workflow_run(
        self,
        workflow_run_id: str,
        order_config: OrderConfig | None = None,
    ) -> Sequence[WorkflowNodeExecution]:
        """
        Return empty list as mock response.

        Args:
            workflow_run_id: The workflow run ID (ignored)
            order_config: Optional configuration for ordering results (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.get_by_workflow_run: workflow_run_id=%s (mock)",
            workflow_run_id,
        )
        return []

    def get_node_last_execution(
        self,
        tenant_id: str,
        app_id: str,
        workflow_id: str,
        node_id: str,
    ) -> WorkflowNodeExecutionModel | None:
        """
        Return None as mock response.

        Args:
            tenant_id: The tenant identifier (ignored)
            app_id: The application identifier (ignored)
            workflow_id: The workflow identifier (ignored)
            node_id: The node identifier (ignored)

        Returns:
            None
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.get_node_last_execution: node_id=%s (mock)",
            node_id,
        )
        return None

    def get_executions_by_workflow_run(
        self,
        tenant_id: str,
        app_id: str,
        workflow_run_id: str,
    ) -> Sequence[WorkflowNodeExecutionModel]:
        """
        Return empty list as mock response.

        Args:
            tenant_id: The tenant identifier (ignored)
            app_id: The application identifier (ignored)
            workflow_run_id: The workflow run identifier (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.get_executions_by_workflow_run: workflow_run_id=%s (mock)",
            workflow_run_id,
        )
        return []

    def get_execution_by_id(
        self,
        execution_id: str,
        tenant_id: str | None = None,
    ) -> WorkflowNodeExecutionModel | None:
        """
        Return None as mock response.

        Args:
            execution_id: The execution identifier (ignored)
            tenant_id: Optional tenant identifier (ignored)

        Returns:
            None
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.get_execution_by_id: execution_id=%s (mock)",
            execution_id,
        )
        return None

    def delete_expired_executions(
        self,
        tenant_id: str,
        before_date: datetime,
        batch_size: int = 1000,
    ) -> int:
        """
        No-op delete operation, return 0.

        Args:
            tenant_id: The tenant identifier (ignored)
            before_date: Delete executions created before this date (ignored)
            batch_size: Maximum number of executions to delete (ignored)

        Returns:
            0
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.delete_expired_executions: tenant_id=%s (no-op)",
            tenant_id,
        )
        return 0

    def delete_executions_by_app(
        self,
        tenant_id: str,
        app_id: str,
        batch_size: int = 1000,
    ) -> int:
        """
        No-op delete operation, return 0.

        Args:
            tenant_id: The tenant identifier (ignored)
            app_id: The application identifier (ignored)
            batch_size: Maximum number of executions to delete (ignored)

        Returns:
            0
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.delete_executions_by_app: tenant_id=%s, app_id=%s (no-op)",
            tenant_id,
            app_id,
        )
        return 0

    def get_expired_executions_batch(
        self,
        tenant_id: str,
        before_date: datetime,
        batch_size: int = 1000,
    ) -> Sequence[WorkflowNodeExecutionModel]:
        """
        Return empty list as mock response.

        Args:
            tenant_id: The tenant identifier (ignored)
            before_date: Get executions created before this date (ignored)
            batch_size: Maximum number of executions to retrieve (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.get_expired_executions_batch: tenant_id=%s (mock)",
            tenant_id,
        )
        return []

    def delete_executions_by_ids(
        self,
        execution_ids: Sequence[str],
    ) -> int:
        """
        No-op delete operation, return 0.

        Args:
            execution_ids: List of execution IDs to delete (ignored)

        Returns:
            0
        """
        logger.debug(
            "MockAPIWorkflowNodeExecutionRepository.delete_executions_by_ids: count=%d (no-op)",
            len(execution_ids) if execution_ids else 0,
        )
        return 0
