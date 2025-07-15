# pyright: reportPrivateImportUsage=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportUnknownVariableType=false, reportUnusedParameter=false

from unittest import mock

import pytest

from dbt_osmosis.core.config import DbtConfiguration, create_dbt_project_context
from dbt_osmosis.core.settings import YamlRefactorContext, YamlRefactorSettings
from dbt_osmosis.core.introspection import (
    get_columns,
    normalize_column_name,
    _find_first,
    _get_setting_for_node,
    _maybe_use_precise_dtype,
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
    ):
        yield


def test_get_columns_simple(yaml_context: YamlRefactorContext, fresh_caches):
    """
    既知のテーブル (例: 'customers') で get_columns フローをテストします。
    """
    node = yaml_context.project.manifest.nodes["model.jaffle_shop_duckdb.customers"]
    cols = get_columns(yaml_context, node)
    assert "customer_id" in cols


def test_find_first():
    """_find_first ユーティリティ関数をテストします。"""
    data = [1, 2, 3, 4]
    assert _find_first(data, lambda x: x > 2) == 3
    assert _find_first(data, lambda x: x > 4) is None
    assert _find_first(data, lambda x: x > 4, default=999) == 999


@pytest.mark.parametrize(
    "input_col,expected",
    [
        ('"My_Col"', "My_Col"),
        ("my_col", "MY_COL"),
    ],
)
def test_normalize_column_name_snowflake(input_col, expected):
    """Snowflake アダプタの列名の正規化をテストします。"""
    # For snowflake, if quoted - we preserve case but strip quotes, otherwise uppercase
    assert normalize_column_name(input_col, "snowflake") == expected


def test_normalize_column_name_others():
    """他のアダプタの列名の正規化をテストします。"""
    # For other adapters, we only strip outer quotes but do not uppercase or lowercase for now
    assert normalize_column_name('"My_Col"', "duckdb") == "My_Col"
    assert normalize_column_name("my_col", "duckdb") == "my_col"


def test_maybe_use_precise_dtype_numeric():
    """
    numeric_precision_and_scale が有効な場合、
    _maybe_use_precise_dtype が data_type を使用していることを確認します。
    """
    from dbt.adapters.base.column import Column

    col = Column("col1", "DECIMAL(18,3)", None)  # data_type and dtype
    settings = YamlRefactorSettings(numeric_precision_and_scale=True)
    result = _maybe_use_precise_dtype(col, settings, node=None)
    assert result == "DECIMAL(18,3)"


def test_maybe_use_precise_dtype_string():
    """
    string_length が True の場合、
    col.dtype ('VARCHAR' の可能性があります) の代わりに 
    col.data_type ('varchar(256)' など) を使用します。
    """
    from dbt.adapters.base.column import Column

    col = Column("col1", "VARCHAR(256)", None)
    settings = YamlRefactorSettings(string_length=True)
    result = _maybe_use_precise_dtype(col, settings, node=None)
    assert result == "VARCHAR(256)"


def test_get_setting_for_node_basic():
    """
    _get_setting_for_node が node.meta などから読み取ることができることを確認します。
    特定のメタ フィールドを持つようにノードをモックします。
    """
    node = mock.Mock()
    node.config.extra = {}
    node.meta = {
        "dbt-osmosis-options": {
            "test-key": "test-value",
        }
    }
    # key = "test-key", which means we look for 'dbt-osmosis-options' => "test-key"
    val = _get_setting_for_node("test-key", node=node, col=None, fallback=None)
    assert val == "test-value"
