---
sidebar_position: 2
---
# CLI の概要

以下は、dbt-osmosis が現在提供しているコマンドの概要です。各コマンドは、以下の追加オプションもサポートしています。

- `--dry-run` : ディスクへの変更の書き込みを防止します。
- `--check` : 変更が行われた場合にゼロ以外のコードで終了します。
- `--fqn` : [dbt の FQN](https://docs.getdbt.com/reference/node-selection/syntax#the-fqn-method) セグメントでノードをフィルタリングします。
- `--disable-introspection` : ウェアハウスへのクエリを実行せずに実行します（オフラインの場合に便利です）。多くの場合、`--catalog-path` と組み合わせて使用されます。
- `--catalog-path` : 事前に構築された `catalog.json` から列を読み込みます。

その他の便利なフラグについては、以下の各コマンドで説明します。

## YAML 管理

**以下のコマンドはすべて** `dbt-osmosis yaml <command>` の下にあります。

### Organize

`dbt_project.yml` の **宣言的** な設定に基づいて、スキーマ YAML ファイルを再構成します。具体的には、以下の処理を行います。

- ドキュメント化されていないモデルやソースについて、不足している YAML ファイルをブートストラップします。
- 設定したルール（`+dbt-osmosis:` キー）に従って、既存の YAML ファイルを移動またはマージします。

```bash
dbt-osmosis yaml organize [--project-dir] [--profiles-dir] [--target] [--fqn ...] [--dry-run] [--check]
```

よく使用されるオプション:

- `--auto-apply` : 確認メッセージを表示せずにすべてのファイルの場所の変更を適用します
- `--disable-introspection` + `--catalog-path=/path/to/catalog.json` : ウェアハウスに接続されていない場合

### Document

列レベルのドキュメントを上流ノードから下流ノードに渡します（深い継承）。具体的には、以下の操作を実行できます。

- データベース（または `catalog.json`）には存在するが、YAML には存在しない列を追加します。
- データベースに存在しない列を削除します（他のステップと併用する場合はオプションです）。
- 列を並べ替えます（並べ替え設定と組み合わせる場合はオプションです。下記参照）。
- 上流モデルからタグ、説明、メタフィールドを継承します。

```bash
dbt-osmosis yaml document [--project-dir] [--profiles-dir] [--target] [--fqn ...] [--dry-run] [--check]
```

よく使用されるオプション:

- `--force-inherit-descriptions` : 既存の説明がプレースホルダーの場合に上書きします。
- `--use-unrendered-descriptions` : Jinja ベースのドキュメント (`{{ doc(...) }}` など) を継承できるようにします。
- `--skip-add-columns`、`--skip-add-data-types`、`--skip-merge-meta`、`--skip-add-tags` など: 変更を制限したい場合。
- `--synthesize` : ChatGPT/OpenAI を使用して不足しているドキュメントを自動生成します (下記の *Synthesis* を参照)

### Refactor

`organize` と `document` の両方を正しい順序で **組み合わせ** します。通常、実行が推奨されるコマンドは次のとおりです。

- `dbt_project.yml` ルールに一致するように YAML ファイルを作成または移動します。
- ウェアハウスまたはカタログの列が最新であることを確認します。
- 説明とメタデータを継承します。
- 必要に応じて列を並べ替えます。

```bash
dbt-osmosis yaml refactor [--project-dir] [--profiles-dir] [--target] [--fqn ...] [--dry-run] [--check]
```

よく使用されるオプション:

- `--auto-apply`
- `--force-inherit-descriptions`、`--use-unrendered-descriptions`
- `--skip-add-data-types`、`--skip-add-columns` など
- `--synthesize` は ChatGPT/OpenAI で不足しているドキュメントを自動生成します

### YAMLコマンドでよく使用されるフラグ

- `--fqn=staging.some_subfolder` ：特定のサブフォルダまたは dbt ls の結果のみを対象とする
- `--check` ：dbt-osmosis が変更を加える可能性がある場合にCIを失敗させる
- `--dry-run` ：変更内容をディスクに書き込まずにプレビューする
- `--catalog-path=target/catalog.json` ：ライブクエリを回避する
- `--disable-introspection` ：ウェアハウスクエリを完全にスキップする
- `--auto-apply` ：ファイル移動の手動確認をスキップする

### Synthesis （試験的）

`dbt-osmosis yaml refactor`（または`document`）に`--synthesize`フラグを渡すと、dbt-osmosisはOpenAIのAPI（ChatGPTなど）を使用して**不足しているドキュメントを生成**しようとします。`[openai]`エクストラがインストールされている必要があります。

```bash
pip install "dbt-osmosis[openai]"
```

この機能により、大規模なドキュメントのスキャフォールディングが容易になりますが、自動生成されたテキストは常に確認して改良してください。

## SQL

これらのコマンドを使用すると、SQL スニペット (Jinja を含む) を直接コンパイルまたは実行できます:

### Run

SQL ステートメントまたは dbt Jinja ベースのクエリを実行します。

```bash
dbt-osmosis sql run "select * from {{ ref('my_model') }} limit 50"
```

結果は表形式で標準出力に返されます。複数のクエリを並列実行するには `--threads` を使用します（通常は一度に1つのステートメントを実行します）。

### Compile

SQL文（Jinjaを含む）をコンパイルしますが、実行はしません。マクロ、参照、Jinjaロジックを素早く検証するのに便利です。

```bash
dbt-osmosis sql compile "select * from {{ ref('my_model') }}"
```

コンパイルされた SQL を stdout に出力します。

## Workbench

以下の機能を備えた [Streamlit](https://streamlit.io/) アプリケーションを起動します。

- REPL のような環境で、dbt モデルを探索およびクエリ実行できます。
- 並列コンパイルされた SQL を提供します。
- クエリのリアルタイム反復処理を提供します。

```bash
dbt-osmosis workbench [--project-dir] [--profiles-dir] [--host] [--port]
```
