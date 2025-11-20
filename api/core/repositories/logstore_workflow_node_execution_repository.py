"""
LogStore implementation of WorkflowNodeExecutionRepository.

This repository stores workflow node execution logs in Alibaba Cloud LogStore
using an append-only model with nanosecond timestamp versions.
"""

import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any, Union

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from configs import dify_config
from core.model_runtime.utils.encoders import jsonable_encoder
from core.workflow.entities import WorkflowNodeExecution
from core.workflow.enums import NodeType, WorkflowNodeExecutionMetadataKey, WorkflowNodeExecutionStatus
from core.workflow.repositories.workflow_node_execution_repository import OrderConfig, WorkflowNodeExecutionRepository
from core.workflow.workflow_type_encoder import WorkflowRuntimeTypeConverter
from extensions.ext_logstore import get_logstore_client
from libs.helper import extract_tenant_id
from models import Account, CreatorUserRole, EndUser
from models.workflow import WorkflowNodeExecutionTriggeredFrom

logger = logging.getLogger(__name__)


class LogStoreWorkflowNodeExecutionRepository(WorkflowNodeExecutionRepository):
    """
    LogStore implementation of WorkflowNodeExecutionRepository.

    This implementation stores node executions in LogStore using append-only INSERT
    operations with nanosecond timestamp versions. Each save() call creates a new version.
    """

    def __init__(
        self,
        session_factory: sessionmaker | Engine,
        user: Union[Account, EndUser],
        app_id: str | None,
        triggered_from: WorkflowNodeExecutionTriggeredFrom | None,
    ):
        """
        Initialize the LogStore repository with context information.

        Args:
            session_factory: Not used for LogStore, kept for interface compatibility
            user: Account or EndUser object containing tenant_id, user ID, and role information
            app_id: App ID for filtering by application (can be None)
            triggered_from: Source of the execution trigger (SINGLE_STEP or WORKFLOW_RUN)
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
            "Initialized LogStoreWorkflowNodeExecutionRepository: tenant=%s, app=%s, triggered_from=%s",
            self._tenant_id,
            self._app_id,
            self._triggered_from,
        )

    def save(self, execution: WorkflowNodeExecution) -> None:
        """
        Save node execution metadata to LogStore (without inputs/outputs/process_data).

        This method saves the node execution state and metadata. The actual execution
        data (inputs, outputs, process_data) is saved separately via save_execution_data().

        Args:
            execution: The NodeExecution domain entity to persist
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

        # Prepare metadata
        metadata_json = (
            json.dumps(jsonable_encoder(execution.metadata))
            if execution.metadata
            else None
        )

        # Build INSERT SQL for metadata only
        table_name = dify_config.LOGSTORE_NODE_EXECUTIONS
        sql = f"""
            INSERT INTO {table_name} (
                id, version, tenant_id, app_id, workflow_id, workflow_run_id,
                index, predecessor_node_id, node_execution_id, node_id, node_type, title,
                status, error, elapsed_time, execution_metadata,
                created_by, created_by_role, created_at, finished_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        # Prepare parameters
        params = (
            execution.id,
            version,
            self._tenant_id,
            self._app_id,
            execution.workflow_id,
            execution.workflow_execution_id,
            execution.index,
            execution.predecessor_node_id,
            execution.node_execution_id,
            execution.node_id,
            execution.node_type.value,
            execution.title,
            execution.status.value,
            execution.error,
            execution.elapsed_time,
            metadata_json,
            self._creator_user_id,
            self._creator_user_role.value,
            execution.created_at,
            execution.finished_at,
        )

        try:
            # Execute INSERT
            self._logstore_client.execute_insert(sql, params)
            logger.debug(
                "Saved node execution to LogStore: id=%s, version=%s, status=%s",
                execution.id,
                version,
                execution.status,
            )
        except Exception as e:
            logger.exception(
                "Failed to save node execution to LogStore: id=%s, error=%s",
                execution.id,
                e,
            )
            raise

    def save_execution_data(self, execution: WorkflowNodeExecution):
        """
        Save node execution data (inputs/outputs/process_data) to LogStore.

        This method saves the full execution data including inputs, outputs, and process_data.
        If any of these fields are None, they will not be updated.

        Note: For LogStore, we always INSERT a new version, so this method will save
        all provided fields (inputs, outputs, process_data).

        Args:
            execution: The NodeExecution instance containing the execution data
        """
        # Generate nanosecond timestamp version
        version = self._logstore_client.get_version()

        # Prepare converter for JSON encoding
        converter = WorkflowRuntimeTypeConverter()

        # Prepare JSON fields
        inputs_json = None
        if execution.inputs is not None:
            inputs_json = json.dumps(converter.to_json_encodable(execution.inputs))

        process_data_json = None
        if execution.process_data is not None:
            process_data_json = json.dumps(converter.to_json_encodable(execution.process_data))

        outputs_json = None
        if execution.outputs is not None:
            outputs_json = json.dumps(converter.to_json_encodable(execution.outputs))

        # If all data fields are None, skip the insert
        if inputs_json is None and process_data_json is None and outputs_json is None:
            logger.debug("No execution data to save for node execution: id=%s", execution.id)
            return

        # Build INSERT SQL with execution data
        table_name = dify_config.LOGSTORE_NODE_EXECUTIONS
        sql = f"""
            INSERT INTO {table_name} (
                id, version, tenant_id, app_id, workflow_id, workflow_run_id,
                index, predecessor_node_id, node_execution_id, node_id, node_type, title,
                inputs, process_data, outputs,
                status, error, elapsed_time, execution_metadata,
                created_by, created_by_role, created_at, finished_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        # Prepare metadata
        metadata_json = (
            json.dumps(jsonable_encoder(execution.metadata))
            if execution.metadata
            else None
        )

        # Prepare parameters
        params = (
            execution.id,
            version,
            self._tenant_id,
            self._app_id,
            execution.workflow_id,
            execution.workflow_execution_id,
            execution.index,
            execution.predecessor_node_id,
            execution.node_execution_id,
            execution.node_id,
            execution.node_type.value,
            execution.title,
            inputs_json,
            process_data_json,
            outputs_json,
            execution.status.value,
            execution.error,
            execution.elapsed_time,
            metadata_json,
            self._creator_user_id,
            self._creator_user_role.value,
            execution.created_at,
            execution.finished_at,
        )

        try:
            # Execute INSERT
            self._logstore_client.execute_insert(sql, params)
            logger.debug(
                "Saved node execution data to LogStore: id=%s, version=%s",
                execution.id,
                version,
            )
        except Exception as e:
            logger.exception(
                "Failed to save node execution data to LogStore: id=%s, error=%s",
                execution.id,
                e,
            )
            raise

    def get_by_workflow_run(
        self,
        workflow_run_id: str,
        order_config: OrderConfig | None = None,
    ) -> Sequence[WorkflowNodeExecution]:
        """
        Retrieve all NodeExecution instances for a specific workflow run.

        Uses a CTE with window function to get only the latest version of each node execution.

        Args:
            workflow_run_id: The workflow run ID
            order_config: Optional configuration for ordering results

        Returns:
            A list of NodeExecution instances
        """
        # Build CTE to get latest versions
        table_name = dify_config.LOGSTORE_NODE_EXECUTIONS
        sql = f"""
            WITH latest_versions AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY id ORDER BY version DESC) AS rn
                FROM {table_name}
                WHERE workflow_run_id = %s
            )
            SELECT * FROM latest_versions WHERE rn = 1
        """

        # Add ordering if specified
        if order_config and order_config.order_by:
            order_clause = ", ".join(order_config.order_by)
            direction = order_config.order_direction or "asc"
            sql += f" ORDER BY {order_clause} {direction.upper()}"

        try:
            rows = self._logstore_client.execute_query(sql, (workflow_run_id,))
            return [self._row_to_domain_model(row) for row in rows]
        except Exception as e:
            logger.exception(
                "Failed to get node executions from LogStore: workflow_run_id=%s, error=%s",
                workflow_run_id,
                e,
            )
            raise

    def _row_to_domain_model(self, row: dict[str, Any]) -> WorkflowNodeExecution:
        """
        Convert a database row to a domain model.

        Args:
            row: Database row as dictionary

        Returns:
            WorkflowNodeExecution domain model
        """
        # Parse JSON fields
        inputs = json.loads(row["inputs"]) if row.get("inputs") else None
        process_data = json.loads(row["process_data"]) if row.get("process_data") else None
        outputs = json.loads(row["outputs"]) if row.get("outputs") else None
        metadata = {
            WorkflowNodeExecutionMetadataKey(k): v
            for k, v in json.loads(row["execution_metadata"]).items()
        } if row.get("execution_metadata") else None

        # Convert status to domain enum
        status = WorkflowNodeExecutionStatus(row["status"])

        # Create domain model
        return WorkflowNodeExecution(
            id=row["id"],
            node_execution_id=row.get("node_execution_id"),
            workflow_id=row["workflow_id"],
            workflow_execution_id=row.get("workflow_run_id"),
            index=row["index"],
            predecessor_node_id=row.get("predecessor_node_id"),
            node_id=row["node_id"],
            node_type=NodeType(row["node_type"]),
            title=row["title"],
            inputs=inputs,
            process_data=process_data,
            outputs=outputs,
            status=status,
            error=row.get("error"),
            elapsed_time=row.get("elapsed_time", 0.0),
            metadata=metadata,
            created_at=row["created_at"],
            finished_at=row.get("finished_at"),
        )

