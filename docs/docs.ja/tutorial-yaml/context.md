---
sidebar_position: 2
---
# コンテキスト変数

dbt-osmosis は、`+dbt-osmosis:` パス設定で参照できる 3 つの主要な変数（`{model}`、`{node}`、`{parent}`）を提供します。これらの変数を使用することで、YAML ファイルの配置場所に関する **強力** かつ **動的な** ルールを構築でき、**DRY**（don't repeat yourself）** という原則を遵守できます。

## `{model}`

この変数は、処理対象の**モデル名**に展開されます。モデルファイルの名前が `stg_marketo__leads.sql` の場合、`{model}` は `stg_marketo__leads` になります。

**使用例**

```yaml title="dbt_project.yml"
models:
  your_project_name:
    # A default configuration that places each model's docs in a file named after the model,
    # prefixed with an underscore
    +dbt-osmosis: "_{model}.yml"

    intermediate:
      # Overrides the default in the 'intermediate' folder:
      # places YAMLs in a nested folder path, grouping them in "some/deeply/nested/path/"
      +dbt-osmosis: "some/deeply/nested/path/{model}.yml"
```

### `{model}` を使う理由

- **モデルごとに1ファイル**戦略：`_{model}.yml` => `_stg_marketo__leads.yml`
- モデル名をYAMLファイルに**直接マッピング**することで、簡単に見つけることができます
- 各モデルのメタデータを個別に保存したい場合の**シンプルな**アプローチ

## `{node}`

`{node}` は、マニフェストに表示されるノード オブジェクト全体を提供する **強力な** プレースホルダーです。このオブジェクトには、次のような詳細が含まれます。

- `node.fqn`: ノードを一意に識別するリスト (例: `["my_project", "contacts"]`)
- `node.resource_type`: `model`、`source`、または `seed`
- `node.language`: 通常は `"sql`
- `node.config[materialized]`: モデルのマテリアライズ (例: `"table"`、`"view"`、`"incremental"`)
- `node.tags`: モデル設定で割り当てたタグのリスト
- `node.name`: ノードの名前 (`{model}` と同じですが、`node.name` として取得されます)

この変数を使用すると、ファイルパス内の **任意の** ノード属性を直接参照できます。

**使用例**

```yaml title="dbt_project.yml"
models:
  jaffle_shop:
    # We have a default config somewhere higher up. Now we override for intermediate or marts subfolders.

    intermediate:
      # advanced usage: use a combination of node.fqn, resource_type, language, and name
      +dbt-osmosis: "{node.fqn[0]}/{node.resource_type}_{node.language}/{node.name}.yml"

    marts:
      # more advanced: nest YAML by materialization, then by the first tag.
      +dbt-osmosis: "{node.config[materialized]}/{node.tags[0]}/{node.name}.yml"
```

### クリエイティブなユースケース

1. **YAMLをマテリアライズ順に並べ替える**

   ```yaml
   +dbt-osmosis: "{node.config[materialized]}/{model}.yml"
   ```

   モデルが `table` の場合、ファイルパスは `table/stg_customers.yml` になります。

2. **YAML を特定のタグで並べ替える** (`meta` も使用できます)

   ```yaml
   +dbt-osmosis: "{node.tags[0]}/{model}.yml"
   ```

   最初のタグが `finance` の場合、`finance/my_model.yml` が作成されます。

3. **サブフォルダに分割**

   ```yaml
   +dbt-osmosis: "{node.fqn[-2]}/{model}.yml"
   ```

   これは、FQN配列の「最後から2番目」の要素（通常はサブフォルダ名）を参照します。

4. **複数レベルのグループ化**

   ```yaml
   +dbt-osmosis: "{node.resource_type}/{node.config[materialized]}/{node.name}.yml"
   ```

   モデル、ソース、シードのいずれか、そしてその実体化によってグループ化します。

つまり、YAML ファイル構造をカスタマイズしてモデルのメタデータのより深い側面を反映させたい場合、`{node}` は非常に柔軟です。

## `{parent}`

この変数は、生成される**YAMLファイル**の**直近の親ディレクトリ**を表します。これは通常、`.sql`モデルファイルを含むフォルダと一致します。例えば、次のような場合です:

```
models/
  staging/
    salesforce/
      opportunities.sql
```

`opportunities.sql` の `{parent}` は `salesforce` です。したがって、`+dbt-osmosis: "{parent}.yml"` と実行すると、`staging/salesforce/` フォルダ内に単一の `salesforce.yml` が作成されます（このフォルダ内のすべてのモデルがまとめられます）。

**使用例**

```yaml title="dbt_project.yml"
models:
  jaffle_shop:
    staging:
      # So models in staging/salesforce => salesforce.yml
      # models in staging/marketo => marketo.yml
      # etc.
      +dbt-osmosis: "{parent}.yml"
```

### `{parent}` を使う理由

- **統合** YAML: 特定のフォルダ内のすべてのモデルで単一の YAML を共有します。例えば、2～3 個の「salesforce」モデルの場合は `staging/salesforce/salesforce.yml` を使用します。
- `staging/facebook_ads`、`staging/google_ads` のような **フォルダベース** の組織構造で、各ソースのステージングモデルごとに単一のファイルが必要な場合に最適です。

---

## すべてをまとめる

これらの変数を組み合わせることで、**きめ細かな**制御が可能になります。以下は、すべてを統合した複雑な例です。

```yaml
models:
  my_project:
    super_warehouse:
      +dbt-osmosis: "{parent}/{node.config[materialized]}/{node.tags[0]}_{model}.yml"
```

1. **`{parent}`** => `super_warehouse` 直下のサブフォルダの名前。
2. **`{node.config[materialized]}`** => モデルの実体化に基づいて命名された別のサブフォルダ。
3. **`{node.tags[0]}`** => ファイル名のプレフィックス（例：`marketing_` または `analytics_`）。
4. **`{model}`** => わかりやすいように実際のモデル名。

つまり、`materialized='table'` で最初のタグが `'billing'` であるモデル `super_warehouse/snapshots/payment_stats.sql` がある場合、次のような結果が生成されます。

```
super_warehouse/models/table/billing_payment_stats.yml
```

このアプローチにより、YAML ファイルはコードの編成方法（フォルダ構造）とモデルのメタデータ（マテリアライゼーション、タグなど）の両方を反映でき、手作業によるオーバーヘッドは最小限に抑えられます。

---

**まとめると**、**コンテキスト変数**は dbt-osmosis の動的ファイルルーティングシステムの基盤です。`{model}`、`{node}`、`{parent}` を使用することで、幅広いファイルレイアウトパターンを定義し、dbt-osmosis がすべての一貫性を維持できます。モデルごとに 1 つの YAML、フォルダごとに 1 つの YAML、あるいはタグ、マテリアライゼーション、ノードの FQN に依存するより特殊な配置など、どのような場合でも、dbt-osmosis は宣言された構成に合わせて YAML を自動的に **整理** し、 **更新** します。
