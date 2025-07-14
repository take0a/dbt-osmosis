---
sidebar_position: 1
---
# インストール

## uv でインストール

```bash
uv tool install --with="dbt-<adapter>~=1.9.0" dbt-osmosis
```

これにより、`dbt-osmosis` とその依存パッケージが仮想環境にインストールされ、`dbt-osmosis` 経由でコマンドラインツールとして利用できるようになります。また、導入部分で示したように `uvx` を使って、より一時的な方法で直接実行することもできます。

## pipでインストール

```bash
pip install dbt-osmosis dbt-<adapter>
```

(これにより、現在の Python 環境に `dbt-osmosis` がインストールされます。)
