from __future__ import annotations

import os
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from dbt.artifacts.resources.types import NodeType
from dbt.contracts.graph.nodes import ResultNode

import dbt_osmosis.core.logger as logger

__all__ = [
    "SchemaFileLocation",
    "SchemaFileMigration",
    "MissingOsmosisConfig",
    "_get_yaml_path_template",
    "get_current_yaml_path",
    "get_target_yaml_path",
    "build_yaml_file_mapping",
    "create_missing_source_yamls",
]


@dataclass
class SchemaFileLocation:
    """スキーマ ファイルの現在の場所とターゲットの場所を説明します。"""

    target: Path
    current: Path | None = None
    node_type: NodeType = NodeType.Model

    @property
    def is_valid(self) -> bool:
        """現在の場所とターゲットの場所が有効かどうかを確認します。"""
        valid = self.current == self.target
        logger.debug(":white_check_mark: Checking if schema file location is valid => %s", valid)
        return valid


@dataclass
class SchemaFileMigration:
    """スキーマ ファイルの移行操作について説明します。"""

    output: dict[str, t.Any] = field(
        default_factory=lambda: {"version": 2, "models": [], "sources": []}
    )
    supersede: dict[Path, list[ResultNode]] = field(default_factory=dict)


class MissingOsmosisConfig(Exception):
    """osmosis 設定が見つからない場合に発生します。"""


def _get_yaml_path_template(context: t.Any, node: ResultNode) -> str | None:
    """dbt モデルまたはソースノードの yaml パス テンプレートを取得します。"""
    from dbt_osmosis.core.introspection import _find_first

    if node.resource_type == NodeType.Source:
        def_or_path = context.source_definitions.get(node.source_name)
        if isinstance(def_or_path, dict):
            return def_or_path.get("path")
        return def_or_path

    conf = [
        c.get(k)
        for k in ("dbt-osmosis", "dbt_osmosis")
        for c in (node.config.extra, node.config.meta, node.unrendered_config)
    ]
    path_template = _find_first(t.cast("list[str | None]", conf), lambda v: v is not None)
    if not path_template:
        raise MissingOsmosisConfig(
            f"Config key `dbt-osmosis: <path>` not set for model {node.name}"
        )
    logger.debug(":gear: Resolved YAML path template => %s", path_template)
    return path_template


def get_current_yaml_path(context: t.Any, node: ResultNode) -> t.Union[Path, None]:
    """dbt モデルまたはソースノードの現在の yaml パスを取得します。"""
    if node.resource_type in (NodeType.Model, NodeType.Seed) and getattr(node, "patch_path", None):
        path = Path(context.project.runtime_cfg.project_root).joinpath(
            t.cast(str, node.patch_path).partition("://")[-1]
        )
        logger.debug(":page_facing_up: Current YAML path => %s", path)
        return path
    if node.resource_type == NodeType.Source:
        path = Path(context.project.runtime_cfg.project_root, node.path)
        logger.debug(":page_facing_up: Current YAML path => %s", path)
        return path
    return None


def get_target_yaml_path(context: t.Any, node: ResultNode) -> Path:
    """dbt モデルまたはソースノードのターゲット yaml パスを取得します。"""
    tpl = _get_yaml_path_template(context, node)
    if not tpl:
        logger.warning(":warning: No path template found for => %s", node.unique_id)
        return Path(context.project.runtime_cfg.project_root, node.original_file_path)

    fqn_ = node.fqn
    tags_ = node.tags

    # NOTE: this permits negative index lookups in fqn within format strings
    lr_index: dict[int, str] = {i: s for i, s in enumerate(fqn_)}
    rl_index: dict[str, str] = {
        str(-len(fqn_) + i): s for i, s in enumerate(reversed(fqn_), start=1)
    }
    node.fqn = {**rl_index, **lr_index}  # type: ignore[assignment]

    # NOTE: this permits negative index lookups in tags within format strings
    tags_lr_index: dict[int, str] = {i: s for i, s in enumerate(tags_)}
    tags_rl_index: dict[str, str] = {
        str(-len(tags_) + i): s for i, s in enumerate(reversed(tags_), start=1)
    }
    node.tags = {**tags_rl_index, **tags_lr_index}  # type: ignore[assignment]

    path = Path(context.project.runtime_cfg.project_root, node.original_file_path)
    rendered = tpl.format(node=node, model=node.name, parent=path.parent.name)

    # restore original values
    node.fqn = fqn_
    node.tags = tags_

    segments: list[t.Union[Path, str]] = []

    if node.resource_type == NodeType.Source:
        segments.append(context.project.runtime_cfg.model_paths[0])
    elif rendered.startswith("/"):
        segments.append(context.project.runtime_cfg.model_paths[0])
        rendered = rendered.lstrip("/")
    else:
        segments.append(path.parent)

    if not (rendered.endswith(".yml") or rendered.endswith(".yaml")):
        rendered += ".yml"
    segments.append(rendered)

    path = Path(context.project.runtime_cfg.project_root, *segments)
    logger.debug(":star2: Target YAML path => %s", path)
    return path


def build_yaml_file_mapping(
    context: t.Any, create_missing_sources: bool = False
) -> dict[str, SchemaFileLocation]:
    """dbt モデルとソース ノードの現在の yaml パスとターゲット yaml パスへのマッピングを構築します。"""
    logger.info(":globe_with_meridians: Building YAML file mapping...")

    if create_missing_sources:
        create_missing_source_yamls(context)

    out_map: dict[str, SchemaFileLocation] = {}
    from dbt_osmosis.core.node_filters import _iter_candidate_nodes

    for uid, node in _iter_candidate_nodes(context):
        current_path = get_current_yaml_path(context, node)
        out_map[uid] = SchemaFileLocation(
            target=get_target_yaml_path(context, node).resolve(),
            current=current_path.resolve() if current_path else None,
            node_type=node.resource_type,
        )

    logger.debug(":card_index_dividers: Built YAML file mapping => %s", out_map)
    return out_map


def create_missing_source_yamls(context: t.Any) -> None:
    """dbt_project.yml の dbt-osmosis 変数で定義されているが、
    ノードとして存在しないソースのソースファイルを作成します。

    これは、すべてのソースが dbt プロジェクトマニフェストに確実に含まれるようにするための便利な前処理手順です。
    存在しないソースについては詳細なノード情報がないため、
    ここでは代替コードパスを使用してそれらをブートストラップしています。
    """
    from dbt_osmosis.core.config import _reload_manifest
    from dbt_osmosis.core.introspection import _find_first, get_columns

    if context.project.config.disable_introspection:
        logger.warning(":warning: Introspection is disabled, cannot create missing source YAMLs.")
        return
    logger.info(":factory: Creating missing source YAMLs (if any).")
    database: str = context.project.runtime_cfg.credentials.database
    lowercase: bool = context.settings.output_to_lower

    did_side_effect: bool = False
    for source, spec in context.source_definitions.items():
        if isinstance(spec, str):
            schema = source
            src_yaml_path = spec
        elif isinstance(spec, dict):
            database = t.cast(str, spec.get("database", database))
            schema = t.cast(str, spec.get("schema", source))
            src_yaml_path = t.cast(str, spec["path"])
        else:
            continue

        if _find_first(
            context.project.manifest.sources.values(), lambda s: s.source_name == source
        ):
            logger.debug(
                ":white_check_mark: Source => %s already exists in the manifest, skipping creation.",
                source,
            )
            continue

        src_yaml_path_obj = Path(
            context.project.runtime_cfg.project_root,
            context.project.runtime_cfg.model_paths[0],
            src_yaml_path.lstrip(os.sep),
        )

        def _describe(relation: t.Any) -> dict[str, t.Any]:
            assert relation.identifier, "No identifier found for relation."
            s = {
                "name": relation.identifier.lower() if lowercase else relation.identifier,
                "description": "",
                "columns": [
                    {
                        "name": name.lower() if lowercase else name,
                        "description": meta.comment or "",
                        "data_type": meta.type.lower() if lowercase else meta.type,
                    }
                    for name, meta in get_columns(context, relation).items()
                ],
            }
            if context.settings.skip_add_data_types:
                for col in t.cast(list[dict[str, t.Any]], s["columns"]):
                    _ = col.pop("data_type", None)
            return s

        tables = [
            _describe(relation)
            for relation in context.project.adapter.list_relations(database=database, schema=schema)
        ]
        source_dict = {"name": source, "database": database, "schema": schema, "tables": tables}

        src_yaml_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with src_yaml_path_obj.open("w") as f:
            logger.info(
                ":books: Injecting new source => %s => %s", source_dict["name"], src_yaml_path_obj
            )
            context.yaml_handler.dump({"version": 2, "sources": [source_dict]}, f)
            context.register_mutations(1)

        did_side_effect = True

    if did_side_effect:
        logger.info(
            ":arrows_counterclockwise: Some new sources were created, reloading the project."
        )
        _reload_manifest(context.project)
