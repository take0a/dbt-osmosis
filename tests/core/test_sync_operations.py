# pyright: reportPrivateImportUsage=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportUnknownVariableType=false, reportUnusedParameter=false

from unittest import mock

import pytest

from dbt_osmosis.core.config import DbtConfiguration, create_dbt_project_context
from dbt_osmosis.core.settings import YamlRefactorContext, YamlRefactorSettings
from dbt_osmosis.core.sync_operations import sync_node_to_yaml
from dbt_osmosis.core.schema.writer import commit_yamls


@pytest.fixture(scope="module")
def yaml_context() -> YamlRefactorContext:
    """
    実際の「demo duckdb」プロジェクト用の Yaml リファクタリング コンテキストを作成します。
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


@pytest.fixture(scope="function")
def fresh_caches():
    """
    内部キャッシュにパッチを適用して、各テストが新しい状態で開始されるようにします。
    """
    with (
        mock.patch("dbt_osmosis.core.schema.reader._YAML_BUFFER_CACHE", {}),
    ):
        yield


def test_sync_node_to_yaml(yaml_context: YamlRefactorContext, fresh_caches):
    """
    単一ノードの場合、実際のファイルを使用するか、存在しない場合はファイルを生成することで (dry_run モード)、
    sync_node_to_yaml がエラーなしで実行されることを確認できます。
    """
    node = yaml_context.project.manifest.nodes["model.jaffle_shop_duckdb.customers"]
    sync_node_to_yaml(yaml_context, node, commit=False)


def test_sync_node_to_yaml_versioned(yaml_context: YamlRefactorContext, fresh_caches):
    """バージョン管理されたノードを YAML に同期するテストを行います。"""
    node = yaml_context.project.manifest.nodes["model.jaffle_shop_duckdb.stg_customers.v2"]
    sync_node_to_yaml(yaml_context, node, commit=False)


def test_commit_yamls_no_write(yaml_context: YamlRefactorContext):
    """
    dry_run=True なので、commit_yamls は実際にはディスクに何も書き込まないはずです。
    例外が発生しないようにするだけです。
    """
    commit_yamls(
        yaml_handler=yaml_context.yaml_handler,
        yaml_handler_lock=yaml_context.yaml_handler_lock,
        dry_run=yaml_context.settings.dry_run,
        mutation_tracker=yaml_context.register_mutations,
    )
