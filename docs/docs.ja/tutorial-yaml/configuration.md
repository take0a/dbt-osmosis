---
sidebar_position: 1
---
# 設定

## dbt-osmosis の設定

### モデル

少なくとも、dbt プロジェクト内の各モデルの **フォルダ** (またはサブフォルダ) には、`+dbt-osmosis` ディレクティブを使用して、dbt-osmosis が YAML ファイルを配置する **場所** を指定する必要があります。

```yaml title="dbt_project.yml"
models:
  <your_project_name>:
    +dbt-osmosis: "_{model}.yml"   # Default for entire project

    staging:
      +dbt-osmosis: "{parent}.yml" # Each subfolder lumps docs by folder name

    intermediate:
      # Example of using node.config or node.tags
      +dbt-osmosis: "{node.config[materialized]}/{model}.yml"

    marts:
      # A single schema file for all models in 'marts'
      +dbt-osmosis: "prod.yml"
```

まったく同じ方法で **seeds** に適用することもできます。

```yaml title="dbt_project.yml"
seeds:
  <your_project_name>:
    +dbt-osmosis: "_schema.yml"
```

これにより、seed にも自動的に作成された YAML スキーマが使用されるようになります。

---

### Sources

オプションとして、`vars.dbt-osmosis.sources` にエントリを指定することで、dbt-osmosis が **source** を管理するように設定できます。管理したいソースごとに、以下の手順を実行してください。

```yaml title="dbt_project.yml"
vars:
  dbt-osmosis:
    sources:
      salesforce:
        path: "staging/salesforce/source.yml"
        schema: "salesforce_v2"  # If omitted, defaults to the source name

      marketo: "staging/customer/marketo.yml"
      jira: "staging/project_mgmt/schema.yml"
      github: "all_sources/github.yml"

  # (Optional) columns that match these patterns will be ignored
  column_ignore_patterns:
    - "_FIVETRAN_SYNCED"
    - ".*__key__.namespace"
```

**キーポイント**:

- `vars: dbt-osmosis: sources: <source_name>` は、ソース YAML ファイルの **場所** を設定します。
- ソースがまだ存在しない場合、dbt-osmosis は `yaml organizing` または `yaml refactor` を実行すると、その YAML を自動的に **ブートストラップ** します。
- `schema: salesforce_v2` は、必要に応じてデフォルトのスキーマ名をオーバーライドします。これを省略した場合、dbt-osmosis はソース名をスキーマ名とみなします。
- `column_ignore_patterns` のパターンを使用すると、プロジェクト全体で一時的な列やシステム列をスキップできます。

---

## 動作をきめ細かく制御

dbt-osmosis は、ファイルの配置場所だけでなく、列インジェクション、データ型、継承などの処理方法に関する多くの **調整可能なオプション** を提供します。これらのオプションは、グローバル、フォルダレベル、ノードレベル、さらには列ごとに **複数のレベル** で指定できます。dbt-osmosis はこれらの設定をチェーン状にマージするため、最も具体的な設定が「優先」されます。

### 1. コマンドラインフラグによるグローバルオプション

dbt-osmosis CLI 実行時に、コマンドラインフラグを使用してプロジェクト全体のデフォルトを宣言できます。

```sh
dbt-osmosis yaml refactor \
  --skip-add-columns \
  --skip-add-data-types \
  --skip-merge-meta \
  --skip-add-tags \
  --numeric-precision-and-scale \
  --string-length \
  --force-inherit-descriptions \
  --output-to-lower \
  --add-progenitor-to-meta \
  --sort-by=database
```

これらの**グローバル**設定は、下位レベルで上書きされない限り、**すべての**モデルとソースに適用されます。

### 2. フォルダレベルの +dbt-osmosis-options

これはバージョン 1.1 以降の標準的なアプローチです。`dbt_project.yml` 内で、サブフォルダに `+dbt-osmosis-options` を追加できます。

```yaml title="dbt_project.yml"
models:
  my_project:
    # Blanket rule for entire project
    +dbt-osmosis: "_{model}.yml"

    staging:
      +dbt-osmosis: "{parent}.yml"
      +dbt-osmosis-options:
        skip-add-columns: true
        skip-add-data-types: false
        # Reorder columns alphabetically
        sort-by: "alphabetical"

    intermediate:
      +dbt-osmosis: "{node.config[materialized]}/{model}.yml"
      +dbt-osmosis-options:
        skip-add-tags: true
        output-to-lower: true
      +dbt-osmosis-sort-by: "alphabetical" # Flat keys work too
```

つまり、`staging` フォルダ内のすべてにおいて、データベースからの**新しい**列の追加はスキップされ、既存の列はアルファベット順に並べ替えられますが、データ型はスキップされません（グローバルレベルのデフォルトが維持されます）。一方、`intermediate` モデルではタグの追加がスキップされ、すべての列/データ型が小文字に変換されます。

### 3. SQL ファイルでのノードレベル設定

dbt の `config(...)` を使って、`.sql` ファイルで **ノードレベル** のオーバーライドを指定することもできます。

```jinja
-- models/intermediate/some_model.sql
{{ config(
    materialized='incremental',
    dbt_osmosis_options={
      "skip-add-data-types": True,
      "sort-by": "alphabetical"
    }
) }}

SELECT * FROM ...
```

ここでは、dbt-osmosis に、**この** モデルに限ってデータ型の追加を省略し、列をアルファベット順に並べ替えるように指示しています。これは、フォルダレベルまたはグローバルレベルの設定にマージされます。

### 4. 列ごとのメタ情報

**特定の列** のみの dbt-osmosis の動作をオーバーライドしたい場合は、スキーマ YAML で以下のように記述できます。

```yaml
models:
  - name: some_model
    columns:
      - name: tricky_column
        description: "This column is weird, do not reorder me"
        meta:
          dbt-osmosis-skip-add-data-types: true
          dbt_osmosis_options:
            skip-add-tags: true
```

または、ノードの辞書ベースの定義で確認できます。dbt-osmosis は以下の項目をチェックします:

1. `column.meta["dbt-osmosis-skip-add-data-types"]` または `column.meta["dbt_osmosis_skip_add_data_types"]`
2. `column.meta["dbt-osmosis-options"]` または `dbt_osmosis_options`
3. 次に **node** の meta/config
4. 次にフォルダレベル
5. 最後にグローバルプロジェクトレベル

各レベルで、dbt-osmosis は必要に応じてマージまたはオーバーライドを行います。

---

## よく使用される dbt-osmosis オプションの例

以下は、**任意の** レベル（グローバル、フォルダ、ノード、列）で設定できる一般的なフラグまたはオプションの一覧です。これらの多くは CLI フラグとしても使用できますが、構成で設定すると「デフォルト」になります。

| オプション名 | 目的 |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `skip-add-columns` | `true` の場合、dbt-osmosis はウェアハウスには存在するものの YAML には存在しない列を挿入しません。 |
| `skip-add-source-columns` | `true` の場合、**具体的に** ソースに対して列の挿入をスキップします。ソースのスキーマが広く、モデル用の列のみが必要な場合に便利です。 |
| `skip-add-data-types` | `true` の場合、dbt-osmosis は列の `data_type` フィールドにデータを入力しません。|
| `skip-merge-meta` | `true` の場合、dbt-osmosis は上流モデルから `meta` フィールドを継承またはマージしません。|
| `skip-add-tags` | `true` の場合、dbt-osmosis は上流モデルから `tags` を継承またはマージしません。|
| `numeric-precision-and-scale` | `true` の場合、数値列は型の精度/スケールを保持します (`NUMBER(38, 8)` と `NUMBER` のように)。|
| `string-length` | `true` の場合、文字列列は型の長さを保持します (`VARCHAR(256)` と `VARCHAR` のように)。|
| `force-inherit-descriptions` | `true` の場合、子モデルの列は、子の説明が **空** またはプレースホルダーであっても、常に上流の説明を受け入れます。|
| `output-to-lower` | `true` の場合、YAML 内のすべての列名とデータ型が小文字になります。|
| `sort-by` | `database` または `alphabetical`。dbt-osmosis に列の並べ替え方法を指示します。|
| `prefix` | **fuzzy** マッチングプラグインで使用される特殊な文字列。ステージングで常に列にプレフィックスを付けると、dbt-osmosis はマッチング時にプレフィックスを削除できます。|
| `add-inheritance-for-specified-keys` | 上流から継承する **追加** キー（例: `["policy_tags"]`）のリストを指定します。|

その他多数。多くのフラグは **コマンドライン** 引数 (`--skip-add-tags`、`--skip-merge-meta`、`--force-inherit-descriptions` など) としても存在し、`dbt_project.yml` 内の構成設定を上書きまたは補完できます。

---

## まとめ

**dbt-osmosis** の設定は高度にモジュール化されています。以下の点に注意してください。

1. フォルダごとに `+dbt-osmosis: "<some_path>.yml"` ディレクティブを **必ず** 指定します（これにより、Osmosis は YAML を配置する場所を認識できます）。
2. **オプション**（列のスキップ、データ型の追加など）を **グローバル** に設定します。設定は、CLI フラグ、`+dbt-osmosis-options` を使用したより詳細な **フォルダレベル**、`.sql` の **ノードレベル**、またはメタデータの **列レベル** のいずれかで行います。
3. 最終的な結果がユーザーの最も**具体的な**設定を反映するように、dbt-osmosis がマージとロジックを処理します。

このアプローチにより、モデルごとに 1 つの YAML というシンプルなスタイルから、列やデータ型を選択的にスキップしながら複数のアップストリーム ソースからのドキュメントをマージするより高度な構造まで、あらゆるものを実現できます。
