from __future__ import annotations

import argparse
import importlib
import os
import threading
import time
import typing as t
from dataclasses import dataclass, field
from pathlib import Path
from threading import get_ident
from types import ModuleType

import dbt.flags as dbt_flags
from dbt.adapters.base.impl import BaseAdapter
from dbt.adapters.factory import get_adapter, register_adapter
from dbt.config.runtime import RuntimeConfig
from dbt.context.providers import generate_runtime_macro_context
from dbt.contracts.graph.manifest import Manifest
from dbt.mp_context import get_mp_context
from dbt.parser.manifest import ManifestLoader
from dbt.parser.models import ModelParser
from dbt.parser.sql import SqlBlockParser, SqlMacroParser
from dbt.tracking import disable_tracking
from dbt_common.clients.system import get_env
from dbt_common.context import set_invocation_context

import dbt_osmosis.core.logger as logger

__all__ = [
    "discover_project_dir",
    "discover_profiles_dir",
    "DbtConfiguration",
    "DbtProjectContext",
    "create_dbt_project_context",
    "_reload_manifest",
]

disable_tracking()


def discover_project_dir() -> str:
    """dbt_project.yml を含むディレクトリが見つかった場合はそのディレクトリを返し、
    見つからない場合は現在のディレクトリを返します。
    設定されている場合、まず DBT_PROJECT_DIR をチェックします。
    """
    if "DBT_PROJECT_DIR" in os.environ:
        project_dir = Path(os.environ["DBT_PROJECT_DIR"])
        if project_dir.is_dir():
            logger.info(":mag: DBT_PROJECT_DIR detected => %s", project_dir)
            return str(project_dir.resolve())
        logger.warning(":warning: DBT_PROJECT_DIR %s is not a valid directory.", project_dir)
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        if (p / "dbt_project.yml").exists():
            logger.info(":mag: Found dbt_project.yml at => %s", p)
            return str(p.resolve())
    logger.info(":mag: Defaulting to current directory => %s", cwd)
    return str(cwd.resolve())


def discover_profiles_dir() -> str:
    """profiles.yml を含むディレクトリが見つかった場合はそのディレクトリを返し、
    見つからない場合は ~/.dbt を返します。
    DBT_PROFILES_DIR が設定されている場合は、まずそれがチェックされます。
    """
    if "DBT_PROFILES_DIR" in os.environ:
        profiles_dir = Path(os.environ["DBT_PROFILES_DIR"])
        if profiles_dir.is_dir():
            logger.info(":mag: DBT_PROFILES_DIR detected => %s", profiles_dir)
            return str(profiles_dir.resolve())
        logger.warning(":warning: DBT_PROFILES_DIR %s is not a valid directory.", profiles_dir)
    if (Path.cwd() / "profiles.yml").exists():
        logger.info(":mag: Found profiles.yml in current directory.")
        return str(Path.cwd().resolve())
    home_profiles = str(Path.home() / ".dbt")
    logger.info(":mag: Defaulting to => %s", home_profiles)
    return home_profiles


@dataclass
class DbtConfiguration:
    """dbt プロジェクトの構成。"""

    project_dir: str = field(default_factory=discover_project_dir)
    profiles_dir: str = field(default_factory=discover_profiles_dir)
    target: str | None = None
    profile: str | None = None
    threads: int | None = None
    single_threaded: bool | None = None
    vars: dict[str, t.Any] = field(default_factory=dict)
    quiet: bool = True
    disable_introspection: bool = False  # Internal

    def __post_init__(self) -> None:
        logger.debug(":bookmark_tabs: Setting invocation context with environment variables.")
        set_invocation_context(get_env())
        if self.threads and self.threads > 1:
            self.single_threaded = False


def config_to_namespace(cfg: DbtConfiguration) -> argparse.Namespace:
    """DbtConfiguration を dbt 対応の argparse.Namespace に変換します。"""
    logger.debug(":blue_book: Converting DbtConfiguration to argparse.Namespace => %s", cfg)
    ns = argparse.Namespace(
        project_dir=cfg.project_dir,
        profiles_dir=cfg.profiles_dir,
        target=cfg.target or os.getenv("DBT_TARGET"),
        profile=cfg.profile or os.getenv("DBT_PROFILE"),
        threads=cfg.threads,
        single_threaded=cfg.single_threaded,
        vars=cfg.vars,
        which="parse",
        quiet=cfg.quiet,
        DEBUG=False,
        REQUIRE_RESOURCE_NAMES_WITHOUT_SPACES=False,
    )
    return ns


@dataclass
class DbtProjectContext:
    """以下の参照を含むデータオブジェクト:

    - ロードされた dbt 構成
    - マニフェスト
    - SQL/マクロパーサー

    スレッドセーフのためのミューテックスを備えています。
    アダプタは遅延インスタンス化され、TTL を持つため、
    長時間実行されるプロセスにおける複数の操作間で再利用できます。(これがアイデアです)
    """

    config: DbtConfiguration
    """ランタイム cfg とマニフェストを初期化するために使用される dbt プロジェクトの構成"""
    runtime_cfg: RuntimeConfig
    """コンテキストに関連付けられた dbt プロジェクト ランタイム構成"""
    manifest: Manifest
    """dbtプロジェクトマニフェスト"""
    sql_parser: SqlBlockParser
    """dbt Jinja SQL ブロックのパーサー"""
    macro_parser: SqlMacroParser
    """dbt Jinja マクロのパーサー"""
    connection_ttl: float = 3600.0
    """DB 接続をリサイクルする前に接続を維持する最大時間（秒）。主に非常に長い実行時に役立ちます。"""

    _adapter_mutex: threading.Lock = field(default_factory=threading.Lock, init=False)
    _manifest_mutex: threading.Lock = field(default_factory=threading.Lock, init=False)
    _adapter: BaseAdapter | None = field(default=None, init=False)
    _connection_created_at: dict[int, float] = field(default_factory=dict, init=False)

    @property
    def is_connection_expired(self) -> bool:
        """アダプタの TTL に基づいて、アダプタの有効期限が切れているかどうかを確認します。"""
        expired = (
            time.time() - self._connection_created_at.setdefault(get_ident(), 0.0)
            > self.connection_ttl
        )
        logger.debug(":hourglass_flowing_sand: Checking if connection is expired => %s", expired)
        return expired

    @property
    def adapter(self) -> BaseAdapter:
        """アダプタ インスタンスを取得し、
        現在のインスタンスの有効期限が切れている場合は新しいインスタンスを作成します。"""
        with self._adapter_mutex:
            if not self._adapter:
                logger.info(":wrench: Instantiating new adapter because none is currently set.")
                adapter = _instantiate_adapter(self.runtime_cfg)
                adapter.set_macro_resolver(self.manifest)
                _ = adapter.acquire_connection()
                self._adapter = adapter
                self._connection_created_at[get_ident()] = time.time()
                logger.info(
                    ":wrench: Successfully acquired new adapter connection for thread => %s",
                    get_ident(),
                )
            elif self.is_connection_expired:
                logger.info(
                    ":wrench: Refreshing db connection for thread => %s",
                    get_ident(),
                )
                self._adapter.connections.release()
                self._adapter.connections.clear_thread_connection()
                _ = self._adapter.acquire_connection()
                self._connection_created_at[get_ident()] = time.time()
        return self._adapter

    @property
    def manifest_mutex(self) -> threading.Lock:
        """スレッドの安全性を確保するためにマニフェスト ミューテックスを返します。"""
        return self._manifest_mutex


def _add_cross_project_references(
    manifest: Manifest, dbt_loom: ModuleType, project_name: str
) -> Manifest:
    """dbt-loom で定義されたマニフェストから dbt マニフェストへのプロジェクト間参照を追加します。"""
    loomnodes: list[t.Any] = []
    loom = dbt_loom.dbtLoom(project_name)
    loom_manifests = loom.manifests
    logger.info(":arrows_counterclockwise: Loaded dbt loom manifests!")
    for name, loom_manifest in loom_manifests.items():
        if loom_manifest.get("nodes"):
            loom_manifest_nodes = loom_manifest.get("nodes")
            for _, node in loom_manifest_nodes.items():
                if node.get("access"):
                    node_access = node.get("access")
                    if node_access != "protected":
                        if node.get("resource_type") == "model":
                            loomnodes.append(ModelParser.parse_from_dict(None, node))  # pyright: ignore[reportArgumentType]
        for node in loomnodes:
            manifest.nodes[node.unique_id] = node
        logger.info(
            f":arrows_counterclockwise: added {len(loomnodes)} exposed nodes from {name} to the dbt manifest!"
        )
    return manifest


def _instantiate_adapter(runtime_config: RuntimeConfig) -> BaseAdapter:
    """ランタイム構成に基づいて dbt アダプターをインスタンス化します。"""
    logger.debug(":mag: Registering adapter for runtime config => %s", runtime_config)
    adapter = get_adapter(runtime_config)
    adapter.set_macro_context_generator(t.cast(t.Any, generate_runtime_macro_context))
    adapter.connections.set_connection_name("dbt-osmosis")
    logger.debug(":hammer_and_wrench: Adapter instantiated => %s", adapter)
    return t.cast(BaseAdapter, t.cast(t.Any, adapter))


def create_dbt_project_context(config: DbtConfiguration) -> DbtProjectContext:
    """DbtConfiguration から DbtProjectContext を構築します。"""
    logger.info(":wave: Creating DBT project context using config => %s", config)
    args = config_to_namespace(config)
    dbt_flags.set_from_args(args, args)
    runtime_cfg = RuntimeConfig.from_args(args)

    logger.info(":bookmark_tabs: Registering adapter as part of project context creation.")
    register_adapter(runtime_cfg, get_mp_context())

    loader = ManifestLoader(
        runtime_cfg,
        runtime_cfg.load_dependencies(),
    )
    manifest = loader.load()

    try:
        dbt_loom = importlib.import_module("dbt_loom")
    except ImportError:
        pass
    else:
        manifest = _add_cross_project_references(manifest, dbt_loom, runtime_cfg.project_name)

    manifest.build_flat_graph()
    logger.info(":arrows_counterclockwise: Loaded the dbt project manifest!")

    if not config.disable_introspection:
        adapter = _instantiate_adapter(runtime_cfg)
        runtime_cfg.adapter = adapter  # pyright: ignore[reportAttributeAccessIssue]
        adapter.set_macro_resolver(manifest)

    sql_parser = SqlBlockParser(runtime_cfg, manifest, runtime_cfg)
    macro_parser = SqlMacroParser(runtime_cfg, manifest)

    logger.info(":sparkles: DbtProjectContext successfully created!")
    return DbtProjectContext(
        config=config,
        runtime_cfg=runtime_cfg,
        manifest=manifest,
        sql_parser=sql_parser,
        macro_parser=macro_parser,
    )


def _reload_manifest(context: DbtProjectContext) -> None:
    """dbt プロジェクトマニフェストを再読み込みします。ミューテーションの取得に役立ちます。"""
    logger.info(":arrows_counterclockwise: Reloading the dbt project manifest!")
    loader = ManifestLoader(context.runtime_cfg, context.runtime_cfg.load_dependencies())
    manifest = loader.load()
    manifest.build_flat_graph()
    if not context.config.disable_introspection:
        context.adapter.set_macro_resolver(manifest)
    context.manifest = manifest
    logger.info(":white_check_mark: Manifest reloaded => %s", context.manifest.metadata)
