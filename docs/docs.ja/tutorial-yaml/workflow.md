---
sidebar_position: 5
---
# ワークフロー

## YAML ファイル

dbt-osmosis は、`dbt_project.yml` の設定に基づいて、**宣言的な**方法で YAML ファイルを **管理** します。多くの場合、YAML ファイルを手動で作成する必要はありません。YAML ファイルが存在しない場合は、dbt-osmosis が自動的に生成します。一度設定ルールが確立されると、変更内容は自動的に適用され、dbt-osmosis がそれに応じて YAML ファイルを移動またはマージします。

### Sources

デフォルトでは、**dbt-osmosis** は **dbt マニフェスト** からソースを監視します。`vars: dbt-osmosis: sources` で特定のソースパスを宣言すると、dbt-osmosis は次の処理を実行できます。

- 対象の YAML ファイルがまだ存在しない場合は、**作成** します（ブートストラップ）。
- 対象の YAML ファイルを **実際の** データベーススキーマと**同期** します（`--skip-add-source-columns` を指定しない限り、不足している列を取得します）。
- 対象の YAML ファイルの保存場所が変更された場合は、**移行** します（例: `dbt_project.yml` で `path: "some/new/location.yml"` を更新した場合、dbt-osmosis はそれを移動します）。

**主なメリット**: YAML ソースファイルを手動でスキャフォールディングする必要がなくなります。 `vars: dbt-osmosis:` の下にパスを定義するだけです（オプションでカスタムスキーマも指定できます）。ソースが変更された場合（列や新しいテーブルが追加された場合）、dbt-osmosis はそれに応じて YAML を更新します。

```yaml title="dbt_project.yml"
vars:
  dbt-osmosis:
    sources:
      salesforce:
        path: "staging/salesforce/source.yml"
        schema: "salesforce_v2"
      marketo: "staging/customer/marketo.yml"
```

### Models

同様に、**モデル**は`dbt_project.yml`の`+dbt-osmosis`ディレクティブに基づいて管理されます。モデルの各フォルダ（またはサブフォルダ）について、以下の手順を実行します:

```yaml title="dbt_project.yml"
models:
  my_project:
    +dbt-osmosis: "{parent}.yml"

    intermediate:
      +dbt-osmosis: "{node.config[materialized]}/{model}.yml"

    # etc.

seeds:
  my_project:
    # DON'T FORGET: seeds need a +dbt-osmosis rule too!
    +dbt-osmosis: "_schema.yml"
```

`dbt-osmosis yaml` コマンド（`refactor`、`organize`、`document` など）を実行すると、次のようになります。

- **不足している** YAML ファイルは自動的に **ブートストラップ** されます。
- dbt-osmosis は **既存の** YAML ファイルをマージまたは更新します。
- モデルの名前を変更したり、別のフォルダに移動したりした場合（つまり、`+dbt-osmosis` ルールが変更される場合）、dbt-osmosis は対応する YAML をマージまたは移動して一致させます。

dbt-osmosis は宣言されたファイルパスを適用するため、誤って重複した YAML 参照や古い YAML 参照が作成されることは **ありません**。

---

## dbt-osmosis の実行

日々のドキュメント更新に重点を置く場合でも、大規模なリファクタリングに重点を置く場合でも、dbt-osmosis は **3** つの一般的な方法で起動できます。チームのワークフローに最適な方法を選択してください。これらの方法は相互に排他的ではありません。

### 1. オンデマンド ⭐️

**最もシンプルなアプローチ**：整理整頓したいときやドキュメントを最新にしたいときに、dbt-osmosis を時々実行します。例えば：

```bash
# Example: refactor and see if changes occur
dbt-osmosis yaml refactor --target prod --check
```

**推奨される使用方法**:

- **月次または四半期ごと**の「クリーンアップ」
- **フィーチャーブランチ**でアドホック実行（変更内容を確認し、問題がなければマージする）
- 開発者がスキーマを大幅に変更した際に手動で実行できるようにする

一度の実行で、ルールに従ってすべての内容を更新または再編成できるため、**大きな**価値が得られることがよくあります。

### 2. コミット前フック ⭐️⭐️

ドキュメントとスキーマの整合を**自動化**するには、チームの**コミット前**フックにdbt-osmosisを追加できます。これは、例えば`models/`にある`.sql`ファイルをコミットするたびに自動的に実行されます。

```yaml title=".pre-commit-config.yaml"
repos:
  - repo: https://github.com/z3z1ma/dbt-osmosis
    rev: v1.1.5
    hooks:
      - id: dbt-osmosis
        files: ^models/
        # Optionally specify any arguments, e.g. production target:
        args: [--target=prod]
        additional_dependencies: [dbt-<adapter>]
```

**利点**: コミットごとにドキュメントが更新されるため、ドキュメントが古くなることはありません。
**欠点**: コミットごとに若干のオーバーヘッドが発生しますが、変更されたモデルのみをフィルタリングすれば通常は管理可能です。

### 3. CI/CD ⭐️⭐️⭐️

dbt-osmosis を **継続的インテグレーション** パイプラインに統合することもできます。たとえば、GitHub Action やスタンドアロンスクリプトで次のような操作を実行できます。

1. リポジトリを CI 環境にクローンします。
2. `dbt-osmosis yaml refactor` を実行します。
3. 結果として得られた変更をブランチにコミットするか、プルリクエストを開きます。

```bash title="example.sh"
git clone https://github.com/my-org/my-dbt-project.git
cd my-dbt-project
git checkout -b dbt-osmosis-refactor

dbt-osmosis yaml refactor --target=prod

git commit -am "✨ dbt-osmosis refactor"
git push origin -f
gh pr create
```

**メリット**:

- 自動化されており、PR で **レビュー可能** です。
- 制御された環境で実行することで、開発マシンの負荷を軽減します。

**デメリット**:

- CI の設定が必要です。
- 開発者は PR のレビューとマージを忘れないようにする必要があります。

- ---

**まとめ**、dbt-osmosis は幅広いワークフローに適合します。オンデマンドで実行する場合でも、コミット前のフックとして実行する場合でも、CI パイプラインに統合する場合でも、**ソース** と **モデル** の両方の dbt YAML ファイルを、一貫性のある自動化されたアプローチで維持および更新できます。
