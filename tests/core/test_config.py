# pyright: reportPrivateImportUsage=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportUnknownVariableType=false, reportUnusedParameter=false

import os
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

from dbt_osmosis.core.config import (
    DbtConfiguration,
    config_to_namespace,
    create_dbt_project_context,
    discover_profiles_dir,
    discover_project_dir,
    _reload_manifest,
)
from dbt_osmosis.core.settings import YamlRefactorContext, YamlRefactorSettings


@pytest.fixture(scope="module")
def yaml_context() -> YamlRefactorContext:
    """
    実際の「demo_duckdb」プロジェクト用の YamlRefactorContext を作成します。
    これには、有効な dbt_project.yml、プロファイル、マニフェストが含まれている必要があります。
    """
    cfg = DbtConfiguration(project_dir="demo_duckdb", profiles_dir="demo_duckdb")
    cfg.vars = {"dbt-osmosis": {}}

    project_context = create_dbt_project_context(cfg)
    context = YamlRefactorContext(
        project_context,
        settings=YamlRefactorSettings(
            dry_run=True,
            use_unrendered_descriptions=True,
        ),
    )
    return context


def test_discover_project_dir(tmp_path):
    """
    環境変数が設定されておらず、親に dbt_project.yml が見つからない場合に、
    discover_project_dir が適切にフォールバックすることを保証します。
    """
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        found = discover_project_dir()
        assert str(tmp_path.resolve()) == found
    finally:
        os.chdir(original_cwd)


def test_discover_profiles_dir(tmp_path):
    """
    DBT_PROFILES_DIR が設定されておらず、ローカルの profiles.yml が見つからない場合、
    discover_profiles_dir が ~/.dbt にフォールバックするようにします。
    """
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        found = discover_profiles_dir()
        assert str(Path.home() / ".dbt") == found
    finally:
        os.chdir(original_cwd)


def test_config_to_namespace():
    """
    DbtConfiguration が argparse.Namespace に適切に変換されることをテストします。
    """
    cfg = DbtConfiguration(project_dir="demo_duckdb", profiles_dir="demo_duckdb", target="dev")
    ns = config_to_namespace(cfg)
    assert ns.project_dir == "demo_duckdb"
    assert ns.profiles_dir == "demo_duckdb"
    assert ns.target == "dev"


def test_reload_manifest(yaml_context: YamlRefactorContext):
    """
    実際のプロジェクトでは、_reload_manifest が発生しないことの基本チェック。
    """
    _reload_manifest(yaml_context.project)


def test_adapter_ttl_expiration(yaml_context: YamlRefactorContext):
    """
    TTL が期限切れの場合は、DbtProjectContext.adapter で接続を更新することを確認します。
    time.time にパッチを適用して、大きなジャンプをシミュレートします。
    """
    project_ctx = yaml_context.project
    old_adapter = project_ctx.adapter
    # Force we have an entry in _connection_created_at
    thread_id = threading.get_ident()
    project_ctx._connection_created_at[thread_id] = time.time() - 999999  # artificially old

    with (
        mock.patch.object(old_adapter.connections, "release") as mock_release,
        mock.patch.object(old_adapter.connections, "clear_thread_connection") as mock_clear,
    ):
        new_adapter = project_ctx.adapter
        # The underlying object is the same instance, but the connection is re-acquired
        assert new_adapter == old_adapter
        mock_release.assert_called_once()
        mock_clear.assert_called_once()
