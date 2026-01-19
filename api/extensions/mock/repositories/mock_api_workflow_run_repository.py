"""
Mock implementation of the APIWorkflowRunRepository for performance testing.

This implementation provides no-op write operations and mock read operations,
allowing performance testing of workflow runs without database I/O overhead.
"""

import logging
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from core.workflow.entities import WorkflowExecution
from core.workflow.entities.pause_reason import PauseReason
from libs.infinite_scroll_pagination import InfiniteScrollPagination
from models.enums import WorkflowRunTriggeredFrom
from models.workflow import WorkflowRun
from repositories.api_workflow_run_repository import APIWorkflowRunRepository
from repositories.entities.workflow_pause import WorkflowPauseEntity
from repositories.types import (
    AverageInteractionStats,
    DailyRunsStats,
    DailyTerminalsStats,
    DailyTokenCostStats,
)

logger = logging.getLogger(__name__)


class MockAPIWorkflowRunRepository(APIWorkflowRunRepository):
    """
    Mock implementation of APIWorkflowRunRepository for performance testing.

    This implementation is designed for performance testing by:
    - Skipping all write operations (no database I/O)
    - Returning mock/empty data for read operations
    - Maintaining the same interface as production implementations

    Use this to measure the upper performance limit of workflow execution
    without storage overhead.
    """

    def __init__(self, session_maker: sessionmaker | None = None):
        """
        Initialize the repository.

        Args:
            session_maker: SQLAlchemy sessionmaker (unused, for compatibility)
        """
        logger.info("Mock repository enabled: MockAPIWorkflowRunRepository (no data persistence)")
        logger.debug("MockAPIWorkflowRunRepository.__init__: initializing")

    def save(self, execution: WorkflowExecution) -> None:
        """
        No-op save operation for performance testing.

        Args:
            execution: The WorkflowExecution domain entity (ignored)
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.save: id=%s (no-op)",
            execution.id_,
        )
        # Intentionally do nothing - this is a no-op for performance testing
        pass

    def get_paginated_workflow_runs(
        self,
        tenant_id: str,
        app_id: str,
        triggered_from: WorkflowRunTriggeredFrom | Sequence[WorkflowRunTriggeredFrom],
        limit: int = 20,
        last_id: str | None = None,
        status: str | None = None,
    ) -> InfiniteScrollPagination:
        """
        Return mock empty pagination result.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            triggered_from: Filter by trigger source(s) (ignored)
            limit: Maximum number of records to return (ignored)
            last_id: Cursor for pagination (ignored)
            status: Optional filter by status (ignored)

        Returns:
            Empty InfiniteScrollPagination object
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_paginated_workflow_runs: tenant_id=%s, app_id=%s (mock)",
            tenant_id,
            app_id,
        )
        return InfiniteScrollPagination(data=[], limit=limit, has_more=False)

    def get_workflow_run_by_id(
        self,
        tenant_id: str,
        app_id: str,
        run_id: str,
    ) -> WorkflowRun | None:
        """
        Return None as mock response.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            run_id: Workflow run identifier (ignored)

        Returns:
            None
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_workflow_run_by_id: run_id=%s (mock)",
            run_id,
        )
        return None

    def get_workflow_run_by_id_without_tenant(
        self,
        run_id: str,
    ) -> WorkflowRun | None:
        """
        Return None as mock response.

        Args:
            run_id: Workflow run identifier (ignored)

        Returns:
            None
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_workflow_run_by_id_without_tenant: run_id=%s (mock)",
            run_id,
        )
        return None

    def get_workflow_runs_count(
        self,
        tenant_id: str,
        app_id: str,
        triggered_from: str,
        status: str | None = None,
        time_range: str | None = None,
    ) -> dict[str, int]:
        """
        Return mock zero counts.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            triggered_from: Filter by trigger source (ignored)
            status: Optional filter by status (ignored)
            time_range: Optional time range filter (ignored)

        Returns:
            Dictionary with all counts set to 0
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_workflow_runs_count: tenant_id=%s, app_id=%s (mock)",
            tenant_id,
            app_id,
        )
        return {
            "total": 0,
            "running": 0,
            "succeeded": 0,
            "failed": 0,
            "stopped": 0,
            "partial-succeeded": 0,
        }

    def get_expired_runs_batch(
        self,
        tenant_id: str,
        before_date: datetime,
        batch_size: int = 1000,
    ) -> Sequence[WorkflowRun]:
        """
        Return empty list as mock response.

        Args:
            tenant_id: Tenant identifier (ignored)
            before_date: Only return runs created before this date (ignored)
            batch_size: Maximum number of records to return (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_expired_runs_batch: tenant_id=%s (mock)",
            tenant_id,
        )
        return []

    def delete_runs_by_ids(
        self,
        run_ids: Sequence[str],
    ) -> int:
        """
        No-op delete operation, return 0.

        Args:
            run_ids: Sequence of workflow run IDs to delete (ignored)

        Returns:
            0
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.delete_runs_by_ids: count=%d (no-op)",
            len(run_ids) if run_ids else 0,
        )
        return 0

    def delete_runs_by_app(
        self,
        tenant_id: str,
        app_id: str,
        batch_size: int = 1000,
    ) -> int:
        """
        No-op delete operation, return 0.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            batch_size: Number of records to process in each batch (ignored)

        Returns:
            0
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.delete_runs_by_app: tenant_id=%s, app_id=%s (no-op)",
            tenant_id,
            app_id,
        )
        return 0

    def create_workflow_pause(
        self,
        workflow_run_id: str,
        state_owner_user_id: str,
        state: str,
        pause_reasons: Sequence[PauseReason],
    ) -> WorkflowPauseEntity:
        """
        Mock pause creation - raises NotImplementedError.

        Args:
            workflow_run_id: Identifier of the workflow run to pause
            state_owner_user_id: User ID who owns the pause state
            state: Serialized workflow execution state
            pause_reasons: Reasons for pausing

        Raises:
            NotImplementedError: Pause operations not supported in mock repository
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.create_workflow_pause: workflow_run_id=%s (not implemented)",
            workflow_run_id,
        )
        raise NotImplementedError("Pause operations not supported in mock repository")

    def resume_workflow_pause(
        self,
        workflow_run_id: str,
        pause_entity: WorkflowPauseEntity,
    ) -> WorkflowPauseEntity:
        """
        Mock pause resumption - raises NotImplementedError.

        Args:
            workflow_run_id: Identifier of the workflow run to resume
            pause_entity: The pause entity to resume

        Raises:
            NotImplementedError: Pause operations not supported in mock repository
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.resume_workflow_pause: workflow_run_id=%s (not implemented)",
            workflow_run_id,
        )
        raise NotImplementedError("Pause operations not supported in mock repository")

    def delete_workflow_pause(
        self,
        pause_entity: WorkflowPauseEntity,
    ) -> None:
        """
        Mock pause deletion - no-op.

        Args:
            pause_entity: The pause entity to delete (ignored)
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.delete_workflow_pause: pause_id=%s (no-op)",
            pause_entity.id,
        )
        # Intentionally do nothing
        pass

    def prune_pauses(
        self,
        expiration: datetime,
        resumption_expiration: datetime,
        limit: int | None = None,
    ) -> Sequence[str]:
        """
        Mock pause pruning - return empty list.

        Args:
            expiration: Remove pause states created before this time (ignored)
            resumption_expiration: Remove pause states resumed before this time (ignored)
            limit: Maximum number of records deleted (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.prune_pauses: (mock)",
        )
        return []

    def get_daily_runs_statistics(
        self,
        tenant_id: str,
        app_id: str,
        triggered_from: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timezone: str = "UTC",
    ) -> list[DailyRunsStats]:
        """
        Return empty statistics list.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            triggered_from: Filter by trigger source (ignored)
            start_date: Optional start date filter (ignored)
            end_date: Optional end date filter (ignored)
            timezone: Timezone for date grouping (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_daily_runs_statistics: tenant_id=%s, app_id=%s (mock)",
            tenant_id,
            app_id,
        )
        return []

    def get_daily_terminals_statistics(
        self,
        tenant_id: str,
        app_id: str,
        triggered_from: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timezone: str = "UTC",
    ) -> list[DailyTerminalsStats]:
        """
        Return empty statistics list.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            triggered_from: Filter by trigger source (ignored)
            start_date: Optional start date filter (ignored)
            end_date: Optional end date filter (ignored)
            timezone: Timezone for date grouping (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_daily_terminals_statistics: tenant_id=%s, app_id=%s (mock)",
            tenant_id,
            app_id,
        )
        return []

    def get_daily_token_cost_statistics(
        self,
        tenant_id: str,
        app_id: str,
        triggered_from: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timezone: str = "UTC",
    ) -> list[DailyTokenCostStats]:
        """
        Return empty statistics list.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            triggered_from: Filter by trigger source (ignored)
            start_date: Optional start date filter (ignored)
            end_date: Optional end date filter (ignored)
            timezone: Timezone for date grouping (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_daily_token_cost_statistics: tenant_id=%s, app_id=%s (mock)",
            tenant_id,
            app_id,
        )
        return []

    def get_average_app_interaction_statistics(
        self,
        tenant_id: str,
        app_id: str,
        triggered_from: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timezone: str = "UTC",
    ) -> list[AverageInteractionStats]:
        """
        Return empty statistics list.

        Args:
            tenant_id: Tenant identifier (ignored)
            app_id: Application identifier (ignored)
            triggered_from: Filter by trigger source (ignored)
            start_date: Optional start date filter (ignored)
            end_date: Optional end date filter (ignored)
            timezone: Timezone for date grouping (ignored)

        Returns:
            Empty list
        """
        logger.debug(
            "MockAPIWorkflowRunRepository.get_average_app_interaction_statistics: tenant_id=%s, app_id=%s (mock)",
            tenant_id,
            app_id,
        )
        return []
