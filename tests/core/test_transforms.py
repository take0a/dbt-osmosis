# pyright: reportPrivateImportUsage=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportUnknownVariableType=false

from unittest import mock

import pytest

from dbt_osmosis.core.config import DbtConfiguration, create_dbt_project_context
from dbt_osmosis.core.settings import YamlRefactorContext, YamlRefactorSettings
from dbt_osmosis.core.transforms import (
    inherit_upstream_column_knowledge,
    inject_missing_columns,
    remove_columns_not_in_database,
    sort_columns_alphabetically,
    sort_columns_as_configured,
    sort_columns_as_in_database,
    synchronize_data_types,
)


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
        mock.patch("dbt_osmosis.core.introspection._COLUMN_LIST_CACHE", {}),
        mock.patch("dbt_osmosis.core.schema.reader._YAML_BUFFER_CACHE", {}),
    ):
        yield


def test_inherit_upstream_column_knowledge(yaml_context: YamlRefactorContext, fresh_caches):
    """
    実際のプロジェクト内の一致するすべてのノードで継承ロジックを実行する最小限のテスト。
    """
    inherit_upstream_column_knowledge(yaml_context)


def test_inject_missing_columns(yaml_context: YamlRefactorContext, fresh_caches):
    """
    YAML/マニフェストにない列がDBに存在する場合は、それらを注入します。
    エラーが発生しないことを確認するため、一致するすべてのノードで実行します。
    """
    inject_missing_columns(yaml_context)


def test_remove_columns_not_in_database(yaml_context: YamlRefactorContext, fresh_caches):
    """
    マニフェストにDBに存在しない列が含まれている場合、それらを削除します。
    通常、実際のプロジェクトには余分な列は含まれていないため、これは健全性テストです。
    """
    remove_columns_not_in_database(yaml_context)


def test_sort_columns_as_in_database(yaml_context: YamlRefactorContext, fresh_caches):
    """
    DBが認識する順序で列をソートします。
    duckdbではこの処理は最小限ですが、それでもエラーが発生しないことを保証できます。
    """
    sort_columns_as_in_database(yaml_context)


def test_sort_columns_alphabetically(yaml_context: YamlRefactorContext, fresh_caches):
    """
    実際のプロジェクトの使用時に sort_columns_alphabetically が異常終了しないことを確認します。
    """
    sort_columns_alphabetically(yaml_context)


def test_sort_columns_as_configured(yaml_context: YamlRefactorContext, fresh_caches):
    """
    デフォルトでは、sort_by は 'database' ですが、問題が起きないことを確認しましょう。
    """
    sort_columns_as_configured(yaml_context)


def test_synchronize_data_types(yaml_context: YamlRefactorContext, fresh_caches):
    """
    データ型を DB と同期します。
    """
    synchronize_data_types(yaml_context)
