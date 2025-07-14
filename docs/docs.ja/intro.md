---
sidebar_position: 1
---
# dbt-osmosis 入門

5分以内で**dbt-osmosis** の使い方を学びましょう。

## はじめに

まずは**dbt-osmosis**を実行してください。

### 必要なもの

- [Python](https://www.python.org/downloads/) (3.10+)
- [dbt](https://docs.getdbt.com/docs/core/installation) (1.8.0+)
- または [uv](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)
- 既存の dbt プロジェクト (または [jaffle shop](https://github.com/dbt-labs/jaffle_shop_duckdb) を使って試してみることも可能)

## dbt-osmosis の設定

`dbt_project.yml` ファイルに以下のコードを追加します。この設定例では、プロジェクト内のすべてのモデルについて、同じディレクトリ内に、モデル名にアンダースコアを先頭に付けた YAML ファイルが存在することを dbt-osmosis に指示します。例えば、`my_model` という名前のモデルがある場合、そのモデルと同じディレクトリ内に `_my_model.yml` という名前の YAML ファイルが存在する必要があります。この設定は非常に柔軟で、後ほど説明するように、YAML ファイルを任意の方法で宣言的に構成できます。

```yaml title="dbt_project.yml"
models:
  your_project_name:
    +dbt-osmosis: "_{model}.yml"
seeds:
  your_project_name:
    +dbt-osmosis: "_schema.yml"
```

## dbt-osmosis を実行します

uv(x) を使用する場合:

```bash
uvx --with='dbt-<adapter>==1.9.0' dbt-osmosis yaml refactor
```

または、Python 環境にインストールされている場合:

```bash
dbt-osmosis yaml refactor
```

このコマンドを dbt プロジェクトのルートから実行してください。実行前に Git リポジトリがクリーンであることを確認してください。`<adapter>` を dbt アダプタの名前に置き換えてください（例: `snowflake`、`bigquery`、`redshift`、`postgres`、`athena`、`spark`、`trino`、`sqlite`、`duckdb`、`oracle`、`sqlserver`）。

魔法が繰り広げられるのをご覧ください。✨
