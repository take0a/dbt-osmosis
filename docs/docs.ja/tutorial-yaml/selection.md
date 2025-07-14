---
sidebar_position: 4
---
# 選択

`yaml refactor`、`yaml organizing`、`yaml document` などの **dbt-osmosis** コマンドを実行する際、通常はプロジェクト内のモデルやソースの **一部** にスコープを絞り込む必要があります。これにより、以下のことが可能になります。

- プロジェクト全体ではなく、変更のサブセットに焦点を当てることができます。
- リファクタリングやドキュメント作成の実行速度が向上します。
- 段階的なイテレーションにおけるノイズやリスクを軽減できます。

dbt-osmosis は、これを実行するための**2つの**主要な戦略を提供します:

1. **位置セレクタ** (推奨)
2. **`--fqn` フラグ** (上級ユーザーまたは特殊なケース向け)

## 1. 位置セレクター

**位置セレクター** は、コマンドの後に指定する **フラグ以外の引数** です。**パスまたはモデル名** として解釈されます。基盤となるロジックでは、各位置引数を以下のものと照合しようとします。

- モデル名 (例: `stg_customers`)
- ファイルパス (例: `models/staging/stg_customers.sql`)
- ディレクトリパス (例: `models/staging`)
- ファイルグロブ (例: `marts/**/*.sql`)

つまり、`--` で始まっていないものはすべて、dbt-osmosis がプロジェクトに対して照合を試みる *位置パスまたはノード名* として扱われます。

### コマンド例

```bash
# Select all models in the models/staging directory
dbt-osmosis yaml refactor models/staging
```

この場合、dbt-osmosis は `models/staging` 内の dbt モデルとして認識される **すべての** `.sql` ファイルを処理します。同様に、次のようになります:

```bash
# Select only one model if the name is stg_customers and it exists
dbt-osmosis yaml refactor stg_customers
```

dbt-osmosis は、`stg_customers` という **正確な** 名前を持つノードを検索します。見つかった場合、そのモデルのみを処理します。名前が既知のノードと一致しない場合、dbt-osmosis は `stg_customers` というパスまたはファイルが存在するかどうかを確認します。それが見つからない場合、モデルは選択されません。

#### グロブの使用

シェルがワイルドカードまたは再帰グロブをサポートしている場合:

```bash
# Recursively select all .sql models in marts/ subdirectories
dbt-osmosis yaml refactor marts/**/*.sql
```

これは、`marts/` の下にある **任意の** ネスト レベルのすべての `.sql` ファイルを選択することと同じです。

#### 絶対パス

**絶対**パスまたは相対パスを指定することもできます。例:

```bash
dbt-osmosis yaml refactor /full/path/to/my_project/models/staging/*.sql
```

dbt-osmosis がこれらの `.sql` ファイルを現在の dbt プロジェクトの一部として認識した場合は、それらを含めます。

### dbt-osmosis による位置セレクタの解釈方法

1. **正確なノード名チェック**: 位置引数が既知のモデル名（`stg_customers` など）と **直接一致** する場合、dbt-osmosis はそのノードを選択します。
2. **ファイルまたはディレクトリのチェック**: 引数が有効なパス（相対パスまたは絶対パス）の場合、dbt-osmosis はその下にある認識済みのすべての `.sql` モデル（単一の `.sql` の場合はファイル自体）を含めます。
3. **glob 展開**: シェルが glob を展開する場合、dbt-osmosis は dbt モデルにマッピングされる結果の各パスを選択します。

このアプローチは **直感的** で、通常は部分的なリファクタリングに適しており、高度なフラグよりもエラーが発生しにくくなります。

---

## 2. `--fqn`フラグ

:::caution Caution
これは将来**非推奨**になる可能性があります。まずは位置セレクターの使用をお勧めします。
:::

**`--fqn`** フラグは代替アプローチを提供します。dbt の **FQN** (完全修飾名) には通常、次の情報が含まれます:

- プロジェクト名
- リソースタイプ (`model`、`source`、または `seed`)
- ノードにつながるサブフォルダまたはパッケージ
- 最終的なノード名

dbt-osmosis では、プロジェクト名とリソースタイプのセグメントを**省略** し、FQN の後半部分のみに注目します。例えば、`dbt ls` が次の結果を返すとします。

```
my_project.model.staging.salesforce.contacts
```

次のように指定できます:

```bash
dbt-osmosis yaml refactor --fqn=staging.salesforce.contacts
```

そして、dbt-osmosis はまさにそのノードに一致します。または:

```bash
dbt-osmosis yaml refactor --fqn=staging.salesforce
```

これにより、`staging.salesforce.*` の下の **すべての** ノードが選択され、実質的には `staging/salesforce` サブツリー内のすべてが選択されます。

### `--fqn` を使う理由

- **正確な FQN ベース** の選択。
- dbt の FQN の概念に慣れている場合は、`dbt ls` からコピー/ペーストする方が簡単です。
- **部分セグメント**: 正確なファイルパスは覚えていなくても、必要な dbt FQN はわかっている場合があります。

### 例

```bash
dbt-osmosis yaml refactor --fqn=marts.sales.customers
```

プロジェクト名が「my_project」の場合、dbt-osmosis は内部的にそれを「my_project.model.marts.sales.customers」、つまり**そのモデルのみ** として解釈します。または、

```bash
dbt-osmosis yaml refactor --fqn=staging.salesforce
```

これは、FQN が `staging.salesforce` で始まる **任意の** モデルを選択し、`staging/salesforce/` サブフォルダー内のすべてのモデルをキャプチャします。

### エッジケース / 制限事項

- **現在の** プロジェクトのモデルまたはソースのみを対象としています（アップストリームパッケージは対象外です）。
- 複数のサブフォルダで同じ部分的な FQN が共有されている場合、予想よりも多くの一致が見つかる可能性があります。ただし、dbt の命名規則が適切に構成されている場合は、このようなケースは比較的まれです。

---

## どちらを使うべきですか？

**ユースケースの90%**において、**位置セレクタ**が最も簡単で将来性も高くなります。`--fqn`は廃止される可能性があるためです。通常は、パスまたはノード名を指定するだけで十分です。ただし、高度なユースケースがある場合や、`dbt ls`からFQNをコピー＆ペーストする方が便利だと感じる場合は、`--fqn`も有効な選択肢となります。

---

## まとめ

一般的な使用パターンを簡単に説明します。

- **一度に1つのフォルダ**:

  ```bash
  dbt-osmosis yaml refactor models/staging
  ```

- **特定のモデル**:

  ```bash
  dbt-osmosis yaml document stg_customers
  ```

- **`marts` 内のすべての .sql ファイル**:

  ```bash
  dbt-osmosis yaml organize marts/*.sql
  ```

- **複数のサブフォルダーの部分的な FQN**:

  ```bash
  dbt-osmosis yaml refactor --fqn=staging
  ```

  (すべてのステージング モデルを選択)

どのようなアプローチを採用しても、dbt-osmosis は、選択基準に合致するモデル（および該当する場合はソース）のサブセットに対して、**リファクタリング**、**ドキュメント化**、または**整理**といった通常の作業を実行します。

---

**まとめると**、dbt-osmosis の**選択** メカニズムは、単純なファイルベースのフィルターと高度な FQN ベースのフィルターの両方を処理できるほど柔軟です。ほとんどのタスクでは**位置セレクタ** を使用し、特定のワークフローでこの機能が有効な場合は `--fqn` の使用を検討してください。これにより、dbt-osmosis を必要なノードのみで実行できるようになります。
