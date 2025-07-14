---
sidebar_position: 4
---
# 移行ガイド: dbt-osmosis 1.x.x へのアップグレード

## 1. `vars.dbt-osmosis` 構造の変更

**Old** (pre–1.x.x):

```yaml
vars:
  dbt-osmosis:
    # everything was directly under dbt-osmosis
    <source_name>: ...
    _blacklist:
      - ...
```

**New** (1.x.x+):

```yaml
vars:
  dbt-osmosis:
    sources:
      <source_name>: ...
    column_ignore_patterns:
      - ...
    yaml_settings:
      <kwargs for ruamel.yaml>
```

### 問題の原因

- 以前は、すべてのソース定義を `vars.dbt-osmosis` の直下に配置していました。
- 今後は、すべてのソース定義を `vars.dbt-osmosis.sources` の直下にネストする必要があります。
- `column_ignore_patterns` や `yaml_settings` などのキーは、同じ辞書内ではなく、`dbt-osmosis` の直下に **独自の** トップレベルキーを持つようになりました。

**移行**: `dbt_project.yml` に以下の行がある場合:

```yaml
vars:
  dbt-osmosis:
    salesforce: "staging/salesforce/source.yml"
    # ...
```

これを `sources:` の下にネストする必要があります。

```yaml
vars:
  dbt-osmosis:
    sources:
      salesforce: "staging/salesforce/source.yml"
    # ...
```

---

## 2. CLI フラグの名称変更

以下の CLI フラグは、分かりやすさを考慮して名称が変更されました。

1. `--char-length` → `--string-length`
2. `--numeric-precision` → `--numeric-precision-and-scale`
3. `--catalog-file` → `--catalog-path`

これらの古いフラグをスクリプトに記述している場合は、新しい名前に更新してください。

```bash
# Old (pre-1.x.x)
dbt-osmosis yaml refactor --char-length --catalog-file=target/catalog.json

# New (1.x.x+)
dbt-osmosis yaml refactor --string-length --catalog-path=target/catalog.json
```

---

## 3. ファイル移動時に `--auto-apply` プロンプトを表示

`1.x.x` では、dbt-osmosis が再構築操作を検出すると、`organize` コマンドと `refactor` コマンドの両方でファイル移動の確認を求めるプロンプトが表示されることがあります。デフォルトでは、以下のメッセージが表示されます。

```
Apply the restructure plan? [y/N]
```

### `--auto-apply`

- `--auto-apply` を **渡す** と、自動的に確認が行われ、プロンプトが表示されなくなります（CI/CD で役立ちます）。
- `--auto-apply` を **渡さない** 場合、ファイルのシャッフルを行う際に確認プロンプトが表示されます。

これは **動作** の変更です。以前は、`organize`/`refactor` は対話的な確認ステップなしにファイルを移動していました。

---

## 4. シードには `+dbt-osmosis: <path>` が必要です

`1.x.x` で dbt-osmosis を使用してシードを管理するには、`dbt_project.yml` シード設定に `+dbt-osmosis` ディレクティブを含めることが**必須** になりました。このディレクティブがない場合、dbt-osmosis は例外を発生させます。

**以前** (1.x.x より前) では、シードには何も必要なかったかもしれません。
**現在**:

```yaml
seeds:
  my_project:
    +dbt-osmosis: "_schema.yml"
```

これがないと、YAML 同期でシードが正しく認識されず、エラーが発生します。

---

## 5. より柔軟な設定解決

dbt-osmosis `1.x.x` では、複数のレベルでオプションを設定できます。

- **グローバルデフォルト / フォールバック** (CLI フラグ経由)
- **フォルダレベル** (`+dbt-osmosis-options` 経由の推奨される標準的なアプローチ)
- **ノードレベル** (`.sql` ファイル内の `config(dbt_osmosis_options=...)` 経由)
- **列レベル** (スキーマファイル内の列 `meta:` 経由)

**重要理由**: マージのオーバーライドまたはスキップ、列の小文字化、あいまい一致を処理するためのプレフィックスの指定など、**すべて** 異なる粒度で設定できるようになりました。これには、`prefix` のような新しいキーや、`output-to-lower`、`numeric-precision-and-scale` のようなノードごとまたは列ごとに適用できる既存のキーが含まれます。

フォルダレベルのオーバーライドの例:

```yaml
models:
  my_project:
    staging:
      +dbt-osmosis: "{parent}.yml"
      +dbt-osmosis-options:
        numeric-precision-and-scale: false
        output-to-lower: true
```

`.sql` でのノードレベルのオーバーライドの例:

```sql
{{ config(materialized="view", dbt_osmosis_options={"prefix": "account_"}) }}

SELECT
  id AS account_id,
  ...
FROM ...
```

---

## 6. 継承のデフォルト設定：`--force-inherit-descriptions` を指定しない場合、子ノードのドキュメントは上書きされません

`1.x.x` では、**デフォルト** で、子ノードに既存の列記述が **存在** する場合、dbt-osmosis はそれを上流ノードのドキュメントで上書きしません。これは、上流ノードにドキュメントが存在すると子ノードの記述が上書きされる可能性があった以前のバージョンからの変更です。

- **新機能**: 子ノードのドキュメントを祖先のドキュメントで強制的に上書きするには、`--force-inherit-descriptions` を渡す必要があります。
- 従来の `osmosis_keep_description` によるアプローチは事実上**非推奨** となりました（現在は何も行いません）。新しいアプローチはよりシンプルです。明示的に **強制** 上書きしない限り、子ノードはドキュメントを保持します。

また、**メタ** マージはより**追加的** です。子ノードのメタキーは、完全に上書きされるのではなく、上流ノードと **マージ** されます。

---

## 7. あいまい一致のための新しいプラグインシステム

dbt-osmosis `1.x.x` では**プラグインシステム**（[pluggy](https://pluggy.readthedocs.io) 経由）が追加され、系統全体にわたって列の一致/エイリアスを設定するためのカスタムロジックを提供できるようになりました。組み込みの「あいまい」ロジックには以下が含まれます。

- 大文字/小文字の変換（大文字、小文字、キャメルケース、パスカルケース）。
- プレフィックスの除去（`stg_contact_id → contact_id` のように、列名を体系的に変更する場合）。

高度な命名パターンがある場合は、追加の列一致候補を提供する独自のプラグインを**作成**できます。これは新機能であり、厳密には互換性を破る変更ではありませんが、カスタム継承ロジックに依存している場合は重要です。

---

## 8. PyPI リリースにおける潜在的な変更

安定版リリースを `1.1.x` に統一し、混乱を避けるため、古い `1.0.0` を PyPI から **削除** する予定です。つまり、**もし `1.0.0` を見かけたら**、最終的な安定版ではフラグ名が変更され、設定が構造化されているため、`1.1.x` 以降に直接アップグレードしてください。

---

# 重大な変更点の概要

1. **`vars.dbt-osmosis`** は、`sources:` 以下にソースをネストする必要があります。
2. **CLI フラグの名前が変更されました**:
- `--char-length` → `--string-length`
- `--numeric-precision` → `--numeric-precision-and-scale`
- `--catalog-file` → `--catalog-path`
3. **`organize`/`refactor`** は、`--auto-apply` が使用されない限り、ファイルの移動を促すようになりました。
4. **シード** には、`+dbt-osmosis: <path>` 設定が必要です。
5. `--force-inherit-descriptions` が指定されていない限り、**子の説明** は上書きされません** (以前の `osmosis_keep_description` は廃止されました)。
6. 子/親の**メタマージ** はより追加的になり、上書きが少なくなります。
7. あいまい一致ロジックのための**新しいプラグインシステム**。

---

## 推奨されるアップグレード手順

1. **`dbt_project.yml` を更新します。**
- ソース定義を `vars.dbt-osmosis.sources` 直下に移動します。
- `seeds:` セクションに `+dbt-osmosis: <path>` を追加します。

2. **スクリプトまたはドキュメント内の古いフラグをスキャンします**
- `--char-length`、`--numeric-precision`、`--catalog-file` を新しい同等のフラグに置き換えます。
- プロンプトなしでファイルを移動する場合は、`--auto-apply` を追加します。

3. **上書き戦略を決定します**
- すべての子列に祖先の説明を強制的に適用するという古い動作を維持する場合は、`--force-inherit-descriptions` を渡します。
- それ以外の場合は、新しいデフォルト（子ドキュメントが存在する場合は保持）を使用します。

4. **オプションの確認**:
- 必要に応じて、古い `dbt-osmosis` 設定キー（プレフィックスの使用、skip-add-data-types、skip-merge-meta など）をフォルダレベルまたはノードレベルのオーバーライドに移行します。

5. **新しいプラグインシステムの確認**:
- 複雑な命名戦略を採用している場合や、組み込みのあいまい一致を適用したい場合は、**pluggy** プラグインを作成できます。

6. **検証**:
- プロジェクトで `dbt-osmosis yaml refactor --dry-run` を実行します。変更内容を確認します。
- 問題がなければ、`--dry-run` なしで実行します。

---

# まとめ

**dbt-osmosis 1.x.x** では、YAML 管理フローが **より宣言的** かつ **拡張性** が高まります。この変更により、`dbt_project.yml` や古いフラグを使用しているスクリプトに若干の修正が必要になる場合があります。ただし、移行後は次のようなメリットがあります。

- マージが **より安全** になります（子ドキュメントが意図せず上書きされる可能性が減ります）。
- ソースと無視する列の設定が **よりクリーン** になります。
- 高度な名前変更ロジックのための **プラグインシステム** が利用できます。

このガイドで各ステップを明確にすることで、自信を持って **dbt-osmosis 1.x.x** に移行し、新機能と安定性を享受していただければ幸いです。問題が発生した場合は、GitHub の Issue を作成するか、更新されたドキュメントを参照してさらにサポートを受けてください。