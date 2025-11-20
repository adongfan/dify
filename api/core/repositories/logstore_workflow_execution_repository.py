"""
LogStore implementation of WorkflowExecutionRepository.

This repository stores workflow execution logs in Alibaba Cloud LogStore
using an append-only model with nanosecond timestamp versions.
"""

import json
import logging
from typing import Union

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from configs import dify_config
from core.workflow.entities import WorkflowExecution
from core.workflow.enums import WorkflowExecutionStatus, WorkflowType
from core.workflow.repositories.workflow_execution_repository import WorkflowExecutionRepository
from core.workflow.workflow_type_encoder import WorkflowRuntimeTypeConverter
from extensions.ext_logstore import get_logstore_client
from libs.helper import extract_tenant_id
from models import Account, CreatorUserRole, EndUser
from models.enums import WorkflowRunTriggeredFrom

logger = logging.getLogger(__name__)


class LogStoreWorkflowExecutionRepository(WorkflowExecutionRepository):
    """
    LogStore implementation of WorkflowExecutionRepository.

    This implementation stores workflow executions in LogStore using append-only INSERT
    operations with nanosecond timestamp versions. Each save() call creates a new version.
    """

    def __init__(
        self,
        session_factory: sessionmaker | Engine,
        user: Union[Account, EndUser],
        app_id: str | None,
        triggered_from: WorkflowRunTriggeredFrom | None,
    ):
        """
        Initialize the LogStore repository with context information.

        Args:
            session_factory: Not used for LogStore, kept for interface compatibility
            user: Account or EndUser object containing tenant_id, user ID, and role information
            app_id: App ID for filtering by application (can be None)
            triggered_from: Source of the execution trigger (DEBUGGING or APP_RUN)
        """
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

        # Get LogStore client
        self._logstore_client = get_logstore_client()

        logger.debug(
            "Initialized LogStoreWorkflowExecutionRepository: tenant=%s, app=%s, triggered_from=%s",
            self._tenant_id,
            self._app_id,
            self._triggered_from,
        )

    def save(self, execution: WorkflowExecution):
        """
        Save workflow execution to LogStore using append-only INSERT.

        Each save() creates a new version with a nanosecond timestamp. The LogStore
        table will contain multiple versions of the same execution (id), with the
        highest version representing the latest state.

        Args:
            execution: The WorkflowExecution domain entity to persist
        """
        # Validate required context
        if not self._triggered_from:
            raise ValueError("triggered_from is required in repository constructor")
        if not self._creator_user_id:
            raise ValueError("created_by is required in repository constructor")
        if not self._creator_user_role:
            raise ValueError("created_by_role is required in repository constructor")

        # Generate nanosecond timestamp version
        version = self._logstore_client.get_version()

        # Prepare JSON fields
        graph_json = json.dumps(execution.graph) if execution.graph else None
        inputs_json = json.dumps(execution.inputs) if execution.inputs else None
        outputs_json = (
            json.dumps(WorkflowRuntimeTypeConverter().to_json_encodable(execution.outputs))
            if execution.outputs
            else None
        )

        # Build INSERT SQL (logstore name as table name)
        table_name = dify_config.LOGSTORE_WORKFLOW_RUNS
        sql = f"""
            INSERT INTO {table_name} (
                id, version, tenant_id, app_id, workflow_id, triggered_from,
                type, workflow_version, graph, inputs, outputs,
                status, error, total_tokens, total_steps, exceptions_count,
                created_by, created_by_role, created_at, finished_at, elapsed_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        # Prepare parameters
        params = (
            execution.id_,
            version,
            self._tenant_id,
            self._app_id,
            execution.workflow_id,
            self._triggered_from.value,
            execution.workflow_type.value,
            execution.workflow_version,
            graph_json,
            inputs_json,
            outputs_json,
            execution.status.value,
            execution.error_message or None,
            execution.total_tokens,
            execution.total_steps,
            execution.exceptions_count,
            self._creator_user_id,
            self._creator_user_role.value,
            execution.started_at,
            execution.finished_at,
            execution.elapsed_time,
        )

        try:
            # Execute INSERT
            self._logstore_client.execute_insert(sql, params)
            logger.debug(
                "Saved workflow execution to LogStore: id=%s, version=%s, status=%s",
                execution.id_,
                version,
                execution.status,
            )
        except Exception as e:
            logger.exception(
                "Failed to save workflow execution to LogStore: id=%s, error=%s",
                execution.id_,
                e,
            )
            raise

