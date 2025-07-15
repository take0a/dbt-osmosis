from __future__ import annotations

import typing as t
from collections import defaultdict, deque
from itertools import chain
from pathlib import Path

from dbt.artifacts.resources.types import NodeType
from dbt.contracts.graph.nodes import ResultNode

import dbt_osmosis.core.logger as logger

__all__ = [
    "_is_fqn_match",
    "_is_file_match",
    "_topological_sort",
    "_iter_candidate_nodes",
]


def _is_fqn_match(node: ResultNode, fqns: list[str]) -> bool:
    """部分セグメントに一致する、提供された完全修飾名に基づいてモデルをフィルタリングします。"""
    logger.debug(":mag_right: Checking if node => %s matches any FQNs => %s", node.unique_id, fqns)
    for fqn_str in fqns:
        parts = fqn_str.split(".")
        segment_match = len(node.fqn[1:]) >= len(parts) and all(
            left == right for left, right in zip(parts, node.fqn[1:])
        )
        if segment_match:
            logger.debug(":white_check_mark: FQN matched => %s", fqn_str)
            return True
    return False


def _is_file_match(node: ResultNode, paths: list[Path | str], root: Path | str) -> bool:
    """ノードのファイル パスが、指定されたファイル パスまたは名前のいずれかと一致するかどうかを確認します。"""
    node_path = Path(root, node.original_file_path).resolve()
    yaml_path = None
    if node.patch_path:
        absolute_patch_path = Path(root, node.patch_path.partition("://")[-1]).resolve()
        if absolute_patch_path.exists():
            yaml_path = absolute_patch_path
    for model_or_dir in paths:
        model_or_dir = Path(model_or_dir).resolve()
        if node.name == model_or_dir.stem:
            logger.debug(":white_check_mark: Name match => %s", model_or_dir)
            return True
        if model_or_dir.is_dir():
            if model_or_dir in node_path.parents or yaml_path and model_or_dir in yaml_path.parents:
                logger.debug(":white_check_mark: Directory path match => %s", model_or_dir)
                return True
        if model_or_dir.is_file():
            if model_or_dir.samefile(node_path) or yaml_path and model_or_dir.samefile(yaml_path):
                logger.debug(":white_check_mark: File path match => %s", model_or_dir)
                return True
    return False


def _topological_sort(
    candidate_nodes: list[tuple[str, ResultNode]],
) -> list[tuple[str, ResultNode]]:
    """
    指定された候補ノード（uid、ノード）のペアに対し、依存関係に基づいてトポロジカルソートを実行します。
    循環が検出された場合は、ValueError を送出します。

    カーンのアルゴリズム:
    1) 隣接リストを構築: 親 -> {子, 子, ...}
    (ノード「子」が「親」に依存する場合、親->子というエッジが存在するため)。
    2) すべてのノードの入次数を計算する。
    3) 入次数が 0 であるすべてのノードをキューに集める。
    4) キューから繰り返しポップしてそのノードを「訪問」し、
    そのノードの子ノードの入次数をデクリメントする。
    いずれかの子ノードの入次数が 0 になった場合は、そのノードをキューにプッシュする。
    5) すべてのノードを訪問した場合、有効な位相順序が得られる。
    そうでない場合、循環が存在する。
    """
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    in_degree: defaultdict[str, int] = defaultdict(int)

    all_uids = {uid for uid, _ in candidate_nodes}

    for uid, _ in candidate_nodes:
        in_degree[uid] = 0

    for uid, node in candidate_nodes:
        for dep_uid in node.depends_on_nodes:
            if dep_uid in all_uids:
                adjacency[dep_uid].add(uid)
                in_degree[uid] += 1

    queue: deque[str] = deque([uid for uid, deg in in_degree.items() if deg == 0])
    sorted_uids: list[str] = []

    while queue:
        parent_uid = queue.popleft()
        sorted_uids.append(parent_uid)

        for child_uid in adjacency[parent_uid]:
            in_degree[child_uid] -= 1
            if in_degree[child_uid] == 0:
                queue.append(child_uid)

    if len(sorted_uids) < len(candidate_nodes):
        raise ValueError(
            "Cycle detected in node dependencies. Cannot produce a valid topological order."
        )

    uid_to_node = dict(candidate_nodes)
    return [(uid, uid_to_node[uid]) for uid in sorted_uids]


def _iter_candidate_nodes(
    context: t.Any,  # YamlRefactorContext type will be imported
    include_external: bool = False,
) -> t.Iterator[tuple[str, ResultNode]]:
    """フィルター設定を適用して、dbt プロジェクト マニフェスト内のモデルを反復処理します。"""
    logger.debug(
        ":mag: Filtering nodes (models/sources/seeds) with user-specified settings => %s",
        context.settings,
    )

    def f(node: ResultNode, include_external: bool = False) -> bool:
        """Closure to filter models based on the context settings."""
        if node.resource_type not in (NodeType.Model, NodeType.Source, NodeType.Seed):
            return False
        if node.package_name != context.project.runtime_cfg.project_name and not include_external:
            return False
        if node.resource_type == NodeType.Model and node.config.materialized == "ephemeral":
            return False
        if context.settings.models:
            if (
                not _is_file_match(
                    node, context.settings.models, context.project.runtime_cfg.project_root
                )
                and not include_external
            ):
                return False
        if context.settings.fqn:
            if not _is_fqn_match(node, context.settings.fqn):
                return False
        logger.debug(":white_check_mark: Node => %s passed filtering logic.", node.unique_id)
        return True

    candidate_nodes: list[t.Any] = []
    items = chain(context.project.manifest.nodes.items(), context.project.manifest.sources.items())
    for uid, dbt_node in items:
        if f(dbt_node, include_external):
            candidate_nodes.append((uid, dbt_node))

    for uid, node in _topological_sort(candidate_nodes):
        yield uid, node
