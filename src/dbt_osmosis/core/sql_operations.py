from __future__ import annotations

import uuid

from agate.table import Table  # pyright: ignore[reportMissingTypeStubs]
from dbt.adapters.contracts.connection import AdapterResponse
from dbt.contracts.graph.nodes import ManifestSQLNode
from dbt.node_types import NodeType
from dbt.parser.manifest import process_node
from dbt.task.sql import SqlCompileRunner

import dbt_osmosis.core.logger as logger
from dbt_osmosis.core.config import DbtProjectContext

__all__ = [
    "compile_sql_code",
    "execute_sql_code",
]


def _has_jinja(code: str) -> bool:
    """コード文字列に Jinja トークンが含まれているかどうかを確認します。"""
    logger.debug(":crystal_ball: Checking if code snippet has Jinja => %s", code[:50] + "...")
    return any(token in code for token in ("{{", "}}", "{%", "%}", "{#", "#}"))


def compile_sql_code(context: DbtProjectContext, raw_sql: str) -> ManifestSQLNode:
    """コンテキストのマニフェストとアダプターを使用して jinja SQL をコンパイルします。"""
    logger.info(":zap: Compiling SQL code. Possibly with jinja => %s", raw_sql[:75] + "...")
    tmp_id = str(uuid.uuid4())
    with context.manifest_mutex:
        key = f"{NodeType.SqlOperation}.{context.runtime_cfg.project_name}.{tmp_id}"
        _ = context.manifest.nodes.pop(key, None)

        node = context.sql_parser.parse_remote(raw_sql, tmp_id)
        if not _has_jinja(raw_sql):
            logger.debug(":scroll: No jinja found in the raw SQL, skipping compile steps.")
            return node
        process_node(context.runtime_cfg, context.manifest, node)
        compiled_node = SqlCompileRunner(
            context.runtime_cfg,
            context.adapter,
            node=node,
            node_index=1,
            num_nodes=1,
        ).compile(context.manifest)

        _ = context.manifest.nodes.pop(key, None)

    logger.info(":sparkles: Compilation complete.")
    return compiled_node


def execute_sql_code(context: DbtProjectContext, raw_sql: str) -> tuple[AdapterResponse, Table]:
    """コンテキストのマニフェストとアダプターを使用して Jinja SQL を実行します。"""
    logger.info(":running: Attempting to execute SQL => %s", raw_sql[:75] + "...")
    if _has_jinja(raw_sql):
        comp = compile_sql_code(context, raw_sql)
        sql_to_exec = comp.compiled_code or comp.raw_code
    else:
        sql_to_exec = raw_sql

    resp, table = context.adapter.execute(sql_to_exec, auto_begin=False, fetch=True)
    logger.info(":white_check_mark: SQL execution complete => %s rows returned.", len(table.rows))  # pyright: ignore[reportUnknownArgumentType]
    return resp, table
