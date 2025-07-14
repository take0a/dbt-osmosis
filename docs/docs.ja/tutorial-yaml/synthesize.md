---
sidebar_position: 6
---
# シンセサイズ機能（試験的）

dbt-osmosis の `--synthesize` 機能は、大規模言語モデル（LLM）を活用して、dbt モデルおよび列に不足しているドキュメントを自動生成します。この機能は試験的であり、生成されたコンテンツを慎重に検証する必要があります。

## 概要

LLMクライアントを使用するには、APIキー、ベースURL、LLMクライアントに応じたその他の情報など、環境変数を使用して適切な情報を定義する必要があります。

`--synthesize`フラグは、以下のコマンドで使用できます。

- `dbt-osmosis yaml document`
- `dbt-osmosis yaml refactor`

有効にすると、dbt-osmosisはドキュメントが不足しているモデルと列の説明を生成しようとします。生成されるコンテンツは、SQL構造、既存のコンテキスト、および上流のドキュメントに基づいています。

## サポートされている LLM クライアント

以下の LLM クライアントがサポートされています。

1. **OpenAI**
  - 環境変数:
    - `OPENAI_API_KEY` (必須)
    - `OPENAI_MODEL` (デフォルト: `gpt-4o`)
2. **Azure OpenAI**
  - 環境変数:
    - `AZURE_OPENAI_BASE_URL` (必須)
    - `AZURE_OPENAI_API_KEY` (必須)
    - `AZURE_OPENAI_DEPLOYMENT_NAME` (必須)
    - `AZURE_OPENAI_API_VERSION` (デフォルト: `2025-01-01-preview`)
  - 利用可能なデプロイメント
    - 現在のデプロイメントと、この環境変数の設定に必要な値を確認するには、[Open Ai Azure ポータル](https://oai.azure.com/resource/deployments) にアクセスしてください。
3. **LM Studio**
  - 環境変数:
    - `LM_STUDIO_BASE_URL` (デフォルト: `http://localhost:1234/v1`)
    - `LM_STUDIO_API_KEY` (デフォルト: `lm-studio`)
    - `LM_STUDIO_MODEL` (デフォルト: `local-model`)
  - LM Studio をローカルで使用するための詳細情報と手順については、[LM Studio](https://lmstudio.ai) をご覧ください。
4. **Ollama**
  - 環境変数:
    - `OLLAMA_BASE_URL` (デフォルト: `http://localhost:11434/v1`)
    - `OLLAMA_API_KEY` (デフォルト: `ollama`)
    - `OLLAMA_MODEL` (デフォルト: `llama2:latest`)
  - 利用可能なモデル:
    - 利用可能なモデルの一覧と、Ollama をローカルにインストールして実行する方法については、[Ollama](https://ollama.com) をご覧ください。
5. **Google Gemini**
  - 環境変数:
    - `GOOGLE_GEMINI_BASE_URL` (デフォルト: `https://generativelanguage.googleapis.com/v1beta/openai`)
    - `GOOGLE_GEMINI_API_KEY` (必須)
    - `GOOGLE_GEMINI_MODEL` (デフォルト: `gemini-2.0-flash`)
6. **Anthropic**
  - 環境変数:
    - `ANTHROPIC_BASE_URL` (デフォルト: `https://api.anthropic.com/v1`)
    - `ANTHROPIC_API_KEY` (必須)
    - `ANTHROPIC_MODEL` (デフォルト: `claude-3-5-haiku-latest`)
  - 利用可能なモデル:
    - 利用可能なモデルの完全なリストについては、こちらをご覧ください。 [Anthropic](https://docs.anthropic.com/en/docs/about-claude/models/overview#model-names)

## 環境変数の設定

必要な環境変数を設定するには、`.env` または `.envrc` ファイルを使用します。[direnv](https://direnv.net/) などのツールを使用すると、これらの変数を効率的に管理できます。

`.env` ファイルの例:

```bash
# OpenAI
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_MODEL="gpt-4o"

# Azure OpenAI
export LLM_PROVIDER="azure-openai"
export AZURE_OPENAI_BASE_URL="https://your-azure-openai-instance.openai.azure.com"
export AZURE_OPENAI_API_KEY="your_azure_api_key"
export AZURE_OPENAI_DEPLOYMENT_NAME="your_deployment_name"

# LM Studio
export LLM_PROVIDER="lm-studio"
export LM_STUDIO_BASE_URL="http://localhost:1234/v1"
export LM_STUDIO_API_KEY="lm-studio"
export LM_STUDIO_MODEL="local-model"

# Ollama
export LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://localhost:11434/v1"
export OLLAMA_API_KEY="ollama"
export OLLAMA_MODEL="llama3.1"

# Google Gemini
export LLM_PROVIDER="google-gemini"
export GOOGLE_GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
export GOOGLE_GEMINI_API_KEY="your_google_gemini_api_key"
export GOOGLE_GEMINI_MODEL="gemini-2.0-flash"

# Anthropic
export LLM_PROVIDER="anthropic"
export ANTHROPIC_BASE_URL="https://api.anthropic.com/v1"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export ANTHROPIC_MODEL="claude-3-5-haiku-latest"
```

## 接続のテスト

設定した LLM クライアントへの接続をテストするには、次のコマンドを使用します。

```bash
dbt-osmosis --test-llm
```

- 接続が成功した場合は、「LLM クライアント接続に成功しました」と表示されます。
- 接続に失敗した場合は、「LLM クライアント接続に失敗しました」と表示されます。

## 重要事項

- **試験的機能**: `--synthesize` 機能は試験段階であり、生成された説明文を検証するために人間による検証が必要です。
- **コンテキストの制限**: LLM は、特に特定のコンテキストが LLM のトレーニングデータの範囲外にある場合、必ずしも正確な説明文を生成できるとは限りません。
- **検証が必要**: 自動生成されたコンテンツは必ず確認し、ユースケースに適合していることを確認してください。

## インストール

`--synthesize` 機能を使用するには、`[openai]` エクストラオプションを指定して dbt-osmosis をインストールしてください。

```bash
pip install "dbt-osmosis[openai]"
```

## 使用例

```bash
dbt-osmosis yaml refactor --synthesize
```

このコマンドは次の処理を実行します。

1. YAML ファイルを整理します。
2. 親テーブルから子テーブルに説明を継承し、設定された LLM クライアントを使用して空のフィールドの説明を合成して、不足しているドキュメントを生成します。
