"""Supplementary module for LLM synthesis of dbt documentation."""

from __future__ import annotations

import json
import os
import typing as t
from textwrap import dedent

import openai
from openai import OpenAI

__all__ = [
    "generate_model_spec_as_json",
    "generate_column_doc",
    "generate_table_doc",
]


# Dynamic client creation function
def get_llm_client():
    """
    環境変数に基づいて LLM クライアントとモデル エンジン文字列を作成して返します。

    Returns:
        tuple: (client, model_engine) ここで、client は OpenAI または openai オブジェクトであり、model_engine はモデル名です。
    Raises:
        ValueError: 必要な環境変数が欠落しているか、プロバイダーが無効である場合。
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "openai":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not set for OpenAI provider")
        client = OpenAI(api_key=openai_api_key)
        model_engine = os.getenv("OPENAI_MODEL", "gpt-4o")

    elif provider == "azure-openai":
        openai.api_type = "azure-openai"
        openai.api_base = os.getenv("AZURE_OPENAI_BASE_URL")
        openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        model_engine = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not (openai.api_base and openai.api_key and model_engine):
            raise ValueError(
                "Azure environment variables (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME) not properly set for azure-openai provider"
            )
        # For Azure, the global openai object is used directly (legacy SDK structure preferred)
        return openai, model_engine

    elif provider == "lm-studio":
        client = OpenAI(
            base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
            api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
        )
        model_engine = os.getenv("LM_STUDIO_MODEL", "local-model")

    elif provider == "ollama":
        client = OpenAI(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        )
        model_engine = os.getenv("OLLAMA_MODEL", "llama2:latest")

    elif provider == "google-gemini":
        client = OpenAI(
            base_url=os.getenv(
                "GOOGLE_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
            ),
            api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
        )
        model_engine = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash")

        if not client.api_key:
            raise ValueError(
                "GEMINI environment variables GOOGLE_GEMINI_API_KEY not set for google-gemini provider"
            )

    elif provider == "anthropic":
        client = OpenAI(
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        model_engine = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")

        if not client.api_key:
            raise ValueError(
                "Anthropic environment variables ANTHROPIC_API_KEY not set for anthropic provider"
            )

    else:
        raise ValueError(
            f"Invalid LLM provider '{provider}'. Valid options: openai, azure-openai, google-gemini, anthropic, lm-studio, ollama."
        )

    # Define required environment variables for each provider
    required_env_vars = {
        "openai": ["OPENAI_API_KEY"],
        "azure-openai": [
            "AZURE_OPENAI_BASE_URL",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT_NAME",
        ],
        "lm-studio": ["LM_STUDIO_BASE_URL", "LM_STUDIO_API_KEY"],
        "ollama": ["OLLAMA_BASE_URL", "OLLAMA_API_KEY"],
        "google-gemini": ["GOOGLE_GEMINI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
    }

    # Check for missing environment variables
    missing_vars = [var for var in required_env_vars[provider] if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"ERROR: Missing environment variables for {provider}: {', '.join(missing_vars)}. Please refer to the documentation to set them correctly."
        )

    return client, model_engine


def _create_llm_prompt_for_model_docs_as_json(
    sql_content: str,
    existing_context: str | None = None,
    upstream_docs: list[str] | None = None,
) -> list[dict[str, t.Any]]:
    """モデル全体 (列を含む) を記述する JSON 構造を生成するようにモデルに指示するシステム + 
    ユーザー プロンプトを構築します。"""
    if upstream_docs is None:
        upstream_docs = []

    example_json = dedent(
        """\
    {
      "description": "A short description for the model",
      "columns": [
        {
          "name": "id",
          "description": "Unique identifier for each record",
        },
        {
          "name": "email",
          "description": "User email address",
        }
      ]
    }
    """
    )

    system_prompt = dedent(
        f"""
    You are a helpful SQL Developer and an Expert in dbt.
    You must produce a JSON object that documents a single model and its columns.
    The object must match the structure shown below.
    DO NOT WRITE EXTRA EXPLANATION OR MARKDOWN FENCES, ONLY VALID JSON.

    Example of desired JSON structure:
    {example_json}

    IMPORTANT RULES:
    1. "description" should be short and gleaned from the SQL or the provided docs if possible.
    2. "columns" is an array of objects. Each object MUST contain:
       - "name": the column name
       - "description": short explanation of what the column is
    3. If you have "upstream_docs", you may incorporate them as you see fit, but do NOT invent details.
    4. Do not output any extra text besides valid JSON.
    """
    )

    if max_sql_chars := os.getenv("OSMOSIS_LLM_MAX_SQL_CHARS"):
        if len(sql_content) > int(max_sql_chars):
            sql_content = sql_content[: int(max_sql_chars)] + "... (TRUNCATED)"

    user_message = dedent(
        f"""
    The SQL for the model is:

    >>> SQL CODE START
    {sql_content}
    >>> SQL CODE END

    The context for the model is:
    {existing_context or "(none)"}

    The upstream documentation is:
    {os.linesep.join(upstream_docs)}

    Please return only a valid JSON that matches the structure described above.
    """
    )

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_message.strip()},
    ]


def _create_llm_prompt_for_column(
    column_name: str,
    existing_context: str | None = None,
    table_name: str | None = None,
    upstream_docs: list[str] | None = None,
) -> list[dict[str, str]]:
    """
    単一列の docstring を生成するためのシステム + ユーザープロンプトを構築します。
    最終的な回答は JSON や YAML ではなく、docstring テキストのみである必要があります。

    Args:
        column_name (str): 説明する列の名前。
        existing_context (str | None): 関連するメタデータまたはテーブル定義。
        table_name (str | None): テーブル/モデルの名前 (オプション)。
        upstream_docs (list[str] | None): オプションのドキュメントまたはリファレンス。

    Returns:
        list[dict[str, str]]: LLM のプロンプト メッセージのリスト。
    """
    if upstream_docs is None:
        upstream_docs = []

    table_context = f"in the table '{table_name}'." if table_name else "."

    system_prompt = dedent(
        f"""
    You are a helpful SQL Developer and an Expert in dbt.
    Your job is to produce a concise documentation string
    for a single column {table_context}

    IMPORTANT RULES:
    1. DO NOT output extra commentary or Markdown fences.
    2. Provide only the column description text, nothing else.
    3. If upstream docs exist, you may incorporate them. If none exist,
       a short placeholder is acceptable.
    4. Avoid speculation. Keep it short and relevant.
    """
    )

    user_message = dedent(
        f"""
    The column name is: {column_name}

    Existing context:
    {existing_context or "(none)"}

    Upstream docs:
    {os.linesep.join(upstream_docs)}

    Return ONLY the text suitable for the "description" field.
    """
    )

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_message.strip()},
    ]


def _create_llm_prompt_for_table(
    sql_content: str, table_name: str, upstream_docs: list[str] | None = None
) -> list[dict[str, t.Any]]:
    """
    Builds a system + user prompt instructing the model to produce a string description for a single model/table.

    Args:
        sql_content (str): The SQL code for the table.
        table_name (str): Name of the table/model.
        upstream_docs (list[str] | None): Optional docs or references you might have.

    Returns:
        list[dict[str, t.Any]]: List of prompt messages for the LLM.
    """
    if upstream_docs is None:
        upstream_docs = []

    system_prompt = dedent(
        f"""
    You are a helpful SQL Developer and an Expert in dbt.
    Your job is to produce a concise documentation string
    for a table named {table_name}.

    IMPORTANT RULES:
    1. DO NOT output extra commentary or Markdown fences.
    2. Provide only the column description text, nothing else.
    3. If upstream docs exist, you may incorporate them. If none exist,
       a short placeholder is acceptable.
    4. Avoid speculation. Keep it short and relevant.
    5. DO NOT list out the columns. Only provide a high-level description.
    """
    )

    if max_sql_chars := os.getenv("OSMOSIS_LLM_MAX_SQL_CHARS"):
        if len(sql_content) > int(max_sql_chars):
            sql_content = sql_content[: int(max_sql_chars)] + "... (TRUNCATED)"

    user_message = dedent(
        f"""
    The SQL for the model is:

    >>> SQL CODE START
    {sql_content}
    >>> SQL CODE END

    The upstream documentation is:
    {os.linesep.join(upstream_docs)}

    Please return only the text suitable for the "description" field.
    """
    )

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_message.strip()},
    ]


def generate_model_spec_as_json(
    sql_content: str,
    upstream_docs: list[str] | None = None,
    existing_context: str | None = None,
    temperature: float = 0.3,
) -> dict[str, t.Any]:
    """LLM クライアントを呼び出して、モデルのメタデータと列の JSON 仕様を生成します。

    構造は次のとおりです:
      {
        "description": "...",
        "columns": [
          {"name": "...", "description": "..."},
          ...
        ]
      }

    Args:
        sql_content (str): モデルの完全なSQLコード
        upstream_docs (list[str] | None): コンテキストまたはアップストリームドキュメントを含む文字列のオプションリスト
        model_engine (str): 使用する OpenAI モデル (例: 'gpt-3.5-turbo'、'gpt-4')
        temperature (float): OpenAI完了温度

    Returns:
        dict[str, t.Any]: キー「description」、「columns」を持つ辞書。
    """
    messages = _create_llm_prompt_for_model_docs_as_json(
        sql_content, existing_context, upstream_docs
    )

    client, model_engine = get_llm_client()

    if os.getenv("LLM_PROVIDER", "openai").lower() == "azure-openai":
        # Legacy structure for Azure OpenAI Service
        response = client.ChatCompletion.create(
            engine=model_engine, messages=messages, temperature=temperature
        )
    else:
        # New SDK structure for OpenAI default, LM Studio, Ollama
        response = client.chat.completions.create(
            model=model_engine, messages=messages, temperature=temperature
        )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM returned an empty response")

    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content[content.find("{") : content.rfind("}") + 1]
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("LLM returned invalid JSON:\n" + content)

    return data


def generate_column_doc(
    column_name: str,
    existing_context: str | None = None,
    table_name: str | None = None,
    upstream_docs: list[str] | None = None,
    temperature: float = 0.7,
) -> str:
    """LLM クライアントを呼び出して、テーブル内の 1 つの列のドキュメントを生成します。

    Args:
        column_name (str): 記述する列の名前
        existing_context (str | None): 関連するメタデータまたはテーブル定義
        table_name (str | None): テーブル/モデルの名前（オプション）
        upstream_docs (list[str] | None): オプションのドキュメントや参考資料
        model_engine (str): 使用する OpenAI モデル (例: 'gpt-3.5-turbo')
        temperature (float): OpenAI完了温度

    Returns:
        str: 「説明」フィールドに適した短いドキュメント文字列
    """
    messages = _create_llm_prompt_for_column(
        column_name, existing_context, table_name, upstream_docs
    )

    client, model_engine = get_llm_client()

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "azure-openai":
        response = client.ChatCompletion.create(
            engine=model_engine, messages=messages, temperature=temperature
        )
    else:
        response = client.chat.completions.create(
            model=model_engine, messages=messages, temperature=temperature
        )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM returned an empty response")

    return content.strip()


def generate_table_doc(
    sql_content: str,
    table_name: str,
    upstream_docs: list[str] | None = None,
    temperature: float = 0.7,
) -> str:
    """LLM クライアントを呼び出して、テーブル内の 1 つの列のドキュメントを生成します。

    Args:
        sql_content (str): テーブルのSQLコード
        table_name (str | None): テーブル/モデルの名前（オプション）
        upstream_docs (list[str] | None): オプションのドキュメントや参考資料
        model_engine (str): 使用する OpenAI モデル (例: 'gpt-3.5-turbo')
        temperature (float): OpenAI完了温度

    Returns:
        str: 「説明」フィールドに適した短いドキュメント文字列
    """
    messages = _create_llm_prompt_for_table(sql_content, table_name, upstream_docs)

    client, model_engine = get_llm_client()

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "azure-openai":
        response = client.ChatCompletion.create(
            engine=model_engine, messages=messages, temperature=temperature
        )
    else:
        response = client.chat.completions.create(
            model=model_engine, messages=messages, temperature=temperature
        )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM returned an empty response")

    return content.strip()


if __name__ == "__main__":
    # Kitchen sink
    sample_sql = """
        SELECT
            user_id,
            email,
            created_at,
            is_active
        FROM some_source_table
        WHERE created_at > '2021-01-01'
    """
    docs = [
        "user_id: unique integer ID for each user",
        "email: user email address",
        "created_at: record creation time",
        "is_active: boolean flag indicating active user",
    ]
    model_spec = generate_model_spec_as_json(
        sql_content=sample_sql,
        upstream_docs=docs,
        temperature=0.3,
    )

    print("\n=== Generated Model JSON Spec ===")
    print(json.dumps(model_spec, indent=2))

    col_doc = generate_column_doc(
        column_name="email",
        existing_context="This table tracks basic user information.",
        table_name="user_activity_model",
        upstream_docs=["Stores the user's primary email address."],
        temperature=0.2,
    )
    print("\n=== Single Column Documentation ===")
    print(f"Column: email => {col_doc}")
