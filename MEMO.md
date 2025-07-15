# 環境設定
## uv
```
$ uv venv
$ uv sync
```

test と workbench のため

```
$ uv sync --extra dev --extra workbench
Resolved 128 packages in 28ms
      Built htmlmin==0.1.12
      Built sgmllib3k==1.0.0
Prepared 47 packages in 2.78s
Installed 58 packages in 320ms
 + altair==5.5.0
 + blinker==1.9.0
 + cachetools==5.5.2
 + cfgv==3.4.0
 + contourpy==1.3.2
 + cycler==0.12.1
 + dacite==1.9.2
 + dbt-duckdb==1.9.3
 + distlib==0.3.9
 + duckdb==1.2.2
 + feedparser==6.0.11
 + filelock==3.18.0
 + fonttools==4.57.0
 + gitdb==4.0.12
 + gitpython==3.1.44
 + htmlmin==0.1.12
 + identify==2.6.10
 + imagehash==4.3.1
 + iniconfig==2.1.0
 + joblib==1.4.2
 + kiwisolver==1.4.8
 + matplotlib==3.10.1
 + multimethod==1.12
 + narwhals==1.35.0
 + nodeenv==1.9.1
 + numpy==1.26.4
 + pandas==2.2.3
 + patsy==1.0.1
 + phik==0.12.4
 + pillow==10.4.0
 + platformdirs==4.3.7
 + pre-commit==4.2.0
 + pyarrow==19.0.1
 + pydeck==0.9.1
 + pyparsing==3.2.3
 + pytest==8.3.5
 + pywavelets==1.8.0
 + ruff==0.8.6
 + scipy==1.15.2
 + seaborn==0.13.2
 + setuptools==79.0.0
 + sgmllib3k==1.0.0
 + smmap==5.0.2
 + statsmodels==0.14.4
 + streamlit==1.33.0
 + streamlit-ace==0.1.1
 + streamlit-elements-fluence==0.1.4
 + tenacity==8.5.0
 + toml==0.10.2
 + tornado==6.4.2
 + tqdm==4.67.1
 + typeguard==4.4.2
 + tzdata==2025.2
 + virtualenv==20.30.0
 + visions==0.7.6
 + watchdog==6.0.0
 + wordcloud==1.9.4
 + ydata-profiling==4.12.2
```

# コード解析
## [click](https://click.palletsprojects.com/en/stable/)
- コマンドラインツールを作成するためのモジュール
- 標準ライブラリなら、sys か argparse
- @click.group() すると、サブグループへルーティングされる
    - サブグループは、親.group() でデコレートされる
- @click.version_option で何もしないと importlib.metadata.version() が返る

## cli/main.py
- エントリポイント
- コマンドは、以下の７つ
    - test_llm
        - llm.get_llm_client
        - test_llm_connection
    - yaml refactor
        - DbtConfiguration
        - create_dbt_project_context
        - YamlRefactorContext
        - create_missing_source_yamls(YamlRefactorContext)
        - draft_restructure_delta_plan(YamlRefactorContext)
        - apply_restructure_plan(YamlRefactorContext)
        - inject_missing_columns
        - remove_columns_not_in_database
        - inherit_upstream_column_knowledge
        - sort_columns_as_configured
        - synchronize_data_types
        - synthesize_missing_documentation_with_openai
    - yaml organize
        - （refactor の途中まで）
        - DbtConfiguration
        - create_dbt_project_context
        - YamlRefactorContext
        - create_missing_source_yamls(YamlRefactorContext)
        - draft_restructure_delta_plan(YamlRefactorContext)
        - apply_restructure_plan(YamlRefactorContext) 
    - yaml document
        - （refactor の refacter の部分無し）
        - DbtConfiguration
        - create_dbt_project_context
        - YamlRefactorContext
        - inject_missing_columns
        - inherit_upstream_column_knowledge
        - sort_columns_as_configured
        - synthesize_missing_documentation_with_openai
    - workbench
        - subprocess.run("streamlit", "run", "workbench/app.py")
    - sql run
        - DbtConfiguration
        - create_dbt_project_context
        - core.sql_operations.execute_sql_code
    - sql compile
        - DbtConfiguration
        - create_dbt_project_context
        - core.sql_operations.compile_sql_code

## core/llm.py
- まだ、OpenAI のみ
- get_llm_client
    - AI エンジンとの接続を生成する
- generate_model_spec_as_json
    - モデル全体の description を生成
    - _create_llm_prompt_for_model_docs_as_json
- generate_column_doc
    - カラムの description を生成する
    - _create_llm_prompt_for_column
- generate_table_doc
    - テーブルの description を生成する
    - _create_llm_prompt_for_table

## core/config.py
- dbt のライブラリを import して DbtProjectContext 配下で実体化している
- discover_project_dir
- discover_profiles_dir
- @dataclass DbtProjectContext
    - こいつが欲しいので、↓で作る
- create_dbt_project_context
    - @dataclass DbtConfiguration
        - ↓で変換される元ネタセット
    - config_to_namespace
        - DbtConfiguration を dbt 対応の argparse.Namespace に変換する
    - _add_cross_project_references
    - _instantiate_adapter
_reload_manifest

## core/settings.py
- @dataclass YamlRefactorSettings
    - 設定を ↓に持たせる
- @dataclass YamlRefactorContext
    - こいつが本体
    - __post_init__
        - core.schema.parser.create_yaml_instance

## core/schema/parser.py
- [ruamel.yaml](https://yaml.dev/doc/ruamel.yaml/) ライブラリを使用
- create_yaml_instance
    - ruamel.yaml.YAML を作る
    - ruamel.yaml.YAML.representer.add_representer(str, str_representer)

## core/path_management.py
- @dataclass SchemaFileLocation
- @dataclass SchemaFileMigration
- MissingOsmosisConfig(Exception)
- create_missing_source_yamls
    - core.introspection._find_first
    - context.yaml_handler.dump
    - core.config._reload_manifest

## core.restructuring.py
- @dataclass RestructureDeltaPlan
    - @dataclass RestructureOperation
- draft_restructure_delta_plan
    - _create_operations_for_node
        - _generate_minimal_model_yaml
        - _generate_minimal_source_yaml
- apply_restructure_plan
    - pretty_print_plan
    - core.schema.reader._read_yaml
    - core.schema.writer._write_yaml
    - _remove_models
    - _remove_sources
    - _remove_seeds
    - core.schema.writer.commit_yamls

## core.schema.reader.py
- _read_yaml

## core.schema.writer.py
- _write_yaml
- commit_yamls

## core.transform.py
- @dataclass TransformOperation
- @dataclass TransformPipeline
- _transform_op デコレータ
    - inherit_upstream_column_knowledge
    - inject_missing_columns
    - remove_columns_not_in_database
    - sort_columns_as_in_database
    - sort_columns_alphabetically
    - sort_columns_as_configured
    - synchronize_data_types
    - synthesize_missing_documentation_with_openai

# workbench/app.py
- main
    - _parse_args
    - workbench.components.Dashboard
        - Item(ABC)
    - workbench.components.Editor(Dashboard.Item)
    - workbench.components.Renderer(Dashboard.Item)
    - workbench.components.Preview(Dashboard.Item)
    - workbench.components.Profiler(Dashboard.Item)
    - workbench.components.RssFeed(Dashboard.Item)
    - compile
        - core.sql_operations.compile_sql_code
    - run_query
        - core.sql_operations.execute_sql_code
        - make_json_compat
    - run_profile
        - build_profile_report
        - convert_profile_report_to_html
    - core.config.discover_project_dir
    - core.config.discover_profiles_dir
    - _get_demo_query
    - core.config.create_dbt_project_context
    - sidebar
        - inject_model
        - save_model
        - change_target

## core.sql_operations.py
- execute_sql_code
    - compile_sql_code
        - _has_jinja

## cli 以外から
- 下位互換性インポートを備えた dbt-osmosis コア モジュール？
### core.inheritance.py
### core.introspection.py
### core.logger.py
### core.node_filter.py
### core.osmosis.py
### core.plugins.py
### core.sync_operations.py
### sql.proxy.py

# テスト
## VSCode
```json: .vscode/setting.json
{
    "python.testing.pytestEnabled": true,
}
```

- この設定をすると tests/**/*.py の def test_* と class Test* が使える
    - 関数かクラスかの違いは、よくわからないが、スコープぐらいか？

## pytest
### @pytest.fixture デコレータ
- デコレートされた関数をテスト関数の引数に渡すと、デコレートされた関数の結果が渡される（ので、前処理になる）
- モックを作って渡す。テスト関数ではモックを使ってゴニョゴニョする

### @pytest.mark.parametrize デコレータ
- 引数の値を外出しできる
- タプルのリストでバリエーション指定もできる
- VSCode のテストアイコンは、デコレータを含めた関数の先頭に付く

