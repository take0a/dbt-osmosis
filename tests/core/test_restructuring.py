# pyright: reportPrivateImportUsage=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportUnknownVariableType=false

import logging
from pathlib import Path
from unittest import mock

import pytest

from dbt_osmosis.core.config import DbtConfiguration, create_dbt_project_context
from dbt_osmosis.core.settings import YamlRefactorContext, YamlRefactorSettings
from dbt_osmosis.core.restructuring import (
    apply_restructure_plan,
    draft_restructure_delta_plan,
    pretty_print_plan,
    RestructureOperation,
    RestructureDeltaPlan,
)
from dbt_osmosis.core.path_management import create_missing_source_yamls


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
    with mock.patch("dbt_osmosis.core.schema.reader._YAML_BUFFER_CACHE", {}):
        yield


def test_create_missing_source_yamls(yaml_context: YamlRefactorContext, fresh_caches):
    """
    dbt-osmosis ソースで宣言されているものの、マニフェストに存在しないソース YAML ファイルがある場合は、
    不足しているソース YAML ファイルを作成します。通常、プロジェクトには存在しない可能性があります。
    """
    create_missing_source_yamls(yaml_context)


def test_draft_restructure_delta_plan(yaml_context: YamlRefactorContext, fresh_caches):
    """
    実際のモデルとソースの再構築プランを生成できるようにします。
    通常、すべてが既に整っている場合、このプランは空になることがあります。
    """
    plan = draft_restructure_delta_plan(yaml_context)
    assert plan is not None


def test_apply_restructure_plan(yaml_context: YamlRefactorContext, fresh_caches):
    """
    実際のプロジェクトに再構築プランを適用します（dry_runモード）。
    プランが空または小さい場合でもエラーは発生しません。
    """
    plan = draft_restructure_delta_plan(yaml_context)
    apply_restructure_plan(yaml_context, plan, confirm=False)


def test_pretty_print_plan(caplog):
    """
    テスト pretty_print_plan は、各操作の正しい出力をログに記録します。
    """
    plan = RestructureDeltaPlan(
        operations=[
            RestructureOperation(
                file_path=Path("models/some_file.yml"),
                content={"models": [{"name": "my_model"}]},
            ),
            RestructureOperation(
                file_path=Path("sources/another_file.yml"),
                content={"sources": [{"name": "my_source"}]},
                superseded_paths={Path("old_file.yml"): []},
            ),
        ]
    )
    test_logger = logging.getLogger("test_logger")
    with mock.patch("dbt_osmosis.core.logger.LOGGER", test_logger):
        caplog.clear()
        with caplog.at_level(logging.INFO):
            pretty_print_plan(plan)
    logs = caplog.text
    assert "Restructure plan includes => 2 operations" in logs
    assert "CREATE or MERGE => models/some_file.yml" in logs
    assert "['old_file.yml'] -> sources/another_file.yml" in logs


def test_apply_restructure_plan_confirm_prompt(
    yaml_context: YamlRefactorContext, fresh_caches, capsys
):
    """
    apply_restructure_plan をconfirm=Trueでテストし、
    入力を「n」にモックしてスキップするようにします。
    これにより、ユーザー入力ロジックを確実に処理できます。
    """
    plan = RestructureDeltaPlan(
        operations=[
            RestructureOperation(
                file_path=Path("models/some_file.yml"),
                content={"models": [{"name": "m1"}]},
            )
        ]
    )

    with mock.patch("builtins.input", side_effect=["n"]):
        apply_restructure_plan(yaml_context, plan, confirm=True)
        captured = capsys.readouterr()
        assert "Skipping restructure plan." in captured.err


def test_apply_restructure_plan_confirm_yes(
    yaml_context: YamlRefactorContext, fresh_caches, capsys
):
    """
    上記と同じですが、「y」を入力すると、実際にプランが続行されます。
    （dry_run=True のため、実際の書き込みは行われません）。
    """
    plan = RestructureDeltaPlan(
        operations=[
            RestructureOperation(
                file_path=Path("models/whatever.yml"),
                content={"models": [{"name": "m2"}]},
            )
        ]
    )

    with mock.patch("builtins.input", side_effect=["y"]):
        apply_restructure_plan(yaml_context, plan, confirm=True)
        captured = capsys.readouterr()
        assert "Committing all restructure changes" in captured.err
        assert "Reloading the dbt project manifest" in captured.err
