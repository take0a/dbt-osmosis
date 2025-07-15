# dbt-osmosis

<!--![GitHub Actions](https://github.com/z3z1ma/dbt-osmosis/actions/workflows/master.yml/badge.svg)-->

![PyPI](https://img.shields.io/pypi/v/dbt-osmosis)
[![Downloads](https://static.pepy.tech/badge/dbt-osmosis)](https://pepy.tech/project/dbt-osmosis)
![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)
![black](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dbt-osmosis-playground.streamlit.app/)

[![Scc Count Badge](https://sloc.xyz/github/z3z1ma/dbt-osmosis/)](https://github.com/z3z1ma/dbt-osmosis/)
[![Scc Count Badge](https://sloc.xyz/github/z3z1ma/dbt-osmosis/?category=cocomo)](https://github.com/z3z1ma/dbt-osmosis/)

## dbt-osmosis は初めてですか？

[dbt-osmosis のドキュメントサイト](https://z3z1ma.github.io/dbt-osmosis/)ができました！🎉

dbt-osmosis のより詳しい解説については、ぜひこちらをご覧ください。👇

[![dbt-osmosis](/screenshots/docs_site.png)](https://z3z1ma.github.io/dbt-osmosis/)

## 0.x.x から 1.x.x への移行をお考えですか？

[移行ガイド](https://z3z1ma.github.io/dbt-osmosis/docs/migrating)をご用意しております。🚀

## dbt-osmosisとは？

こんにちは、プロジェクトへようこそ！[dbt-osmosis](https://github.com/z3z1ma/dbt-osmosis)🌊は、開発者エクスペリエンスを大幅に向上させます。4つのコア機能を提供することで、これを実現します。

1. スキーマYAMLの自動管理。

    1a. `dbt-osmosis yaml refactor --project-dir ... --profiles-dir ...`

    > アップストリームでドキュメント化された列に基づいてドキュメントを自動的に生成し、dbt_project.yml で定義された構成可能なルールに基づいて yaml ファイルを整理し、同じルールに基づいて新しい yaml ファイルをスキャフォールディングし、yaml に欠落している場合はデータ ウェアハウス スキーマから列を挿入し、データ ウェアハウスに存在しなくなった列を削除します (整理 -> ドキュメント)

    1b. `dbt-osmosis yaml organize --project-dir ... --profiles-dir ...`

    > dbt_project.yml で定義された設定可能なルールに基づいて yaml ファイルを整理し、同じルールに基づいて新しい yaml ファイルをスキャフォールディングします (ドキュメントの変更はありません)

    1c. `dbt-osmosis yaml document --project-dir ... --profiles-dir ...`

    > 上流の文書化された列に基づいてドキュメントを自動的に生成する（再編成なし）

2. dbt Jinja SQL用のワークベンチ。このワークベンチはstreamlitを利用しており、readmeの上部にあるバッジをクリックすると、jaffle_shopがロードされたstreamlitクラウド上のデモにアクセスできます（追加の`pip install "dbt-osmosis[workbench]"`が必要です）。

    2a. `dbt-osmosis workbench --project-dir ... --profiles-dir ...`

    > 効率の良いアプリを立ち上げましょう。このワークベンチは、VS Codeに依存せずに、Osmosisサーバーとパワーユーザー向けの機能を組み合わせたものと同様の機能を提供します。リアルタイムコンパイル、クエリ実行、Pandasプロファイリングなど、作業中のあらゆるものをワークベンチにコピー＆ペーストするだけで、すべて簡単に実行できます。必要に応じて、アプリの起動と停止を切り替えてください。

____

## コミット前

dbt-osmosis をコミット前フックとして使用できます。これにより、各コミットの前にモデルディレクトリで `dbt-osmosis yaml refactor` コマンドが実行されます。これは、schema.yml ファイルを常に最新の状態に保つ方法の一つです。このコマンドの機能の詳細については、ドキュメントを参照することをお勧めします。

```yaml title=".pre-commit-config.yaml"
repos:
  - repo: https://github.com/z3z1ma/dbt-osmosis
    rev: v1.1.5 # verify the latest version
    hooks:
      - id: dbt-osmosis
        files: ^models/
        args: [--target=prod]
        additional_dependencies: [dbt-<adapter>]
```

___

## ワークベンチ

ワークベンチは、並列エディタとクエリテスターを使用して dbt モデルを操作できる Streamlit アプリです。ユーザーは下のバッジから Streamlit ホストのワークベンチにアクセスして実際に操作できるため、README のこの部分はそのまま残しました。今後のドキュメントは [dbt-osmosis ドキュメントサイト](https://z3z1ma.github.io/dbt-osmosis/) で公開される予定です。

また、ワークベンチには、私自身が時間をかけて開発するだけの、まだ活用されていない価値があると考えています。真に革新的な開発体験への道筋が見えてきたので、その探求を楽しみにしています。

ワークベンチのデモはこちら 👇

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dbt-osmosis-playground.streamlit.app/)

```sh
# NOTE this requires the workbench extra as you can see
pip install "dbt-osmosis[workbench]"

# Command to start server
dbt-osmosis workbench
```

いつでも「r」キーを押せば、ワークベンチをリロードできます。

✔️ dbt エディタで、dbt のコンパイル結果を並べて表示したり、ピボット表示したりできます。

✔️ モデルとワークベンチのテーマ、ライトモードとダークモードを完全に制御できます。

✔️ クエリテスターで、作業中のモデルをテストし、即座にフィードバックを得ることができます。

✔️ データプロファイラー（pandas プロファイリングを活用）

**エディタ**

エディタは、Ctrl + Enter キーを押すか、入力時に動的にモデルをコンパイルできます。非常に高速です！コンパイルと実行には、profiles yml で定義された任意のターゲットを選択できます。

![エディタ](/screenshots/osmosis_editor_main.png?raw=true "dbt-osmosis Workbench")

dbt SQL をワークベンチで実行しているときに、エディタをピボット表示して全体像を把握できます。

![pivot](/screenshots/osmosis_editor_pivot.png?raw=true "dbt-osmosis ピボットレイアウト")

**テストクエリ**

選択したプロファイルに対して dbt モデルをテストし、結果を確認します。これにより、VS Code だけでは実現できない、非常に高速な反復的なフィードバックループを実現できます。

![test-model](/screenshots/osmosis_tester.png?raw=true "dbt-osmosis テストモデル")

**モデル結果のプロファイル**

開発中にコンテキストを切り替えることなく、データセットを即座にプロファイルできます。データセットがメモリに収まる場合、より洗練されたインタラクティブなデータモデリングが可能になります。

![profile-data](/screenshots/osmosis_profile.png?raw=true "dbt-osmosis プロファイルデータ")

**便利なリンクと RSS フィード**

下部に便利なリンクと RSS フィードがあります。🤓

![profile-data](/screenshots/osmosis_links.png?raw=true "dbt-osmosis Profile Data")

___

![graph](https://repobeats.axiom.co/api/embed/df37714aa5780fc79871c60e6fc623f8f8e45c35.svg "Repobeats analytics image")
