from __future__ import annotations

import threading
import typing as t
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import ruamel.yaml
from dbt.contracts.results import CatalogResults

import dbt_osmosis.core.logger as logger

if t.TYPE_CHECKING:
    from dbt_osmosis.core.config import DbtProjectContext

__all__ = [
    "EMPTY_STRING",
    "YamlRefactorSettings",
    "YamlRefactorContext",
]

EMPTY_STRING = ""
"""プレースホルダリストで使用するためのヌル文字列定数。これは常に文書化されていないものとみなされます。"""


@dataclass
class YamlRefactorSettings:
    """yaml ベースのリファクタリング操作の設定。"""

    fqn: list[str] = field(default_factory=list)
    """`dbt ls` によって返されるような完全修飾名の一致を介してモデルをアクションにフィルターします。"""
    models: list[Path | str] = field(default_factory=list)
    """ファイル パスの一致を介してモデルをアクションにフィルターします。"""
    dry_run: bool = False
    """変更をディスクに書き込まないでください。"""
    skip_merge_meta: bool = False
    """yaml ファイル内のアップストリーム メタ フィールドのマージをスキップします。"""
    skip_add_columns: bool = False
    """yaml ファイルに不足している列の追加をスキップします。"""
    skip_add_tags: bool = False
    """yaml ファイルにアップストリーム タグを追加することをスキップします。"""
    skip_add_data_types: bool = False
    """yaml ファイルへのデータ型の追加をスキップします。"""
    skip_add_source_columns: bool = False
    """ソース yaml ファイル内の列の追加を具体的にスキップします。"""
    add_progenitor_to_meta: bool = False
    """列の起源を示すカスタム祖先フィールドをメタセクションに追加します。"""
    numeric_precision_and_scale: bool = False
    """データ型に数値精度を含めます。"""
    string_length: bool = False
    """データ型に文字の長さを含めます。"""
    force_inherit_descriptions: bool = False
    """ノードに有効な説明がある場合でも、上流モデルからの説明の継承を強制します。"""
    use_unrendered_descriptions: bool = False
    """{{ doc(...) }} などの、マニフェスト オブジェクトで事前にレンダリングされるものを保持したレンダリングされていない説明を使用します。"""
    add_inheritance_for_specified_keys: list[str] = field(default_factory=list)
    """継承プロセスに追加のキーを含めます。"""
    output_to_lower: bool = False
    """yaml ファイル内の列名とデータ型の出力を小文字に強制します。"""
    catalog_path: str | None = None
    """ライブ ウェアハウス イントロスペクションの代わりに優先的に使用する dbt catalog.json ファイルへのパス"""
    create_catalog_if_not_exists: bool = False
    """プロジェクトの catalog.json が存在しない場合は生成し、イントロスペクト クエリに使用します。"""


@dataclass
class YamlRefactorContext:
    """以下の参照を含むデータオブジェクト:

    - dbt プロジェクト コンテキスト
    - yaml リファクタリング設定
    - スレッドプール エグゼキューター
    - ruamel.yaml インスタンス
    - プレースホルダ文字列のタプル
    - リファクタリング操作中に増加したミューテーション数
    """

    project: DbtProjectContext  # 循環インポートを避けるための前方参照
    settings: YamlRefactorSettings = field(default_factory=YamlRefactorSettings)
    pool: ThreadPoolExecutor = field(default_factory=ThreadPoolExecutor)
    yaml_handler: ruamel.yaml.YAML = field(
        default_factory=lambda: None
    )  # __post_init__ で設定されます
    yaml_handler_lock: threading.Lock = field(default_factory=threading.Lock)

    placeholders: tuple[str, ...] = (
        EMPTY_STRING,
        "Pending further documentation",
        "No description for this column",
        "Not documented",
        "Undefined",
    )

    _mutation_count: int = field(default=0, init=False)
    _catalog: CatalogResults | None = field(default=None, init=False)

    def register_mutations(self, count: int) -> None:
        """指定した量だけ mutation_count を増やします。"""
        logger.debug(
            ":sparkles: Registering %s new mutations. Current count => %s",
            count,
            self._mutation_count,
        )
        self._mutation_count += count

    @property
    def mutation_count(self) -> int:
        """ミューテーションカウントにアクセスするための読み取り専用プロパティ。"""
        return self._mutation_count

    @property
    def mutated(self) -> bool:
        """コンテキストが変更を実行したかどうかを確認します。"""
        has_mutated = self._mutation_count > 0
        logger.debug(":white_check_mark: Has the context mutated anything? => %s", has_mutated)
        return has_mutated

    @property
    def source_definitions(self) -> dict[str, t.Any]:
        """dbt プロジェクト構成からのソース定義。"""
        c = self.project.runtime_cfg.vars.to_dict()
        toplevel_conf = self._find_first(
            [c.get(k, {}) for k in ["dbt-osmosis", "dbt_osmosis"]], lambda v: bool(v), {}
        )
        return toplevel_conf.get("sources", {})

    @property
    def ignore_patterns(self) -> list[str]:
        """列名は、dbt プロジェクト構成からのパターンを無視します。"""
        c = self.project.runtime_cfg.vars.to_dict()
        toplevel_conf = self._find_first(
            [c.get(k, {}) for k in ["dbt-osmosis", "dbt_osmosis"]], lambda v: bool(v), {}
        )
        return toplevel_conf.get("column_ignore_patterns", [])

    @property
    def yaml_settings(self) -> dict[str, t.Any]:
        """列名は、dbt プロジェクト構成からのパターンを無視します。"""
        c = self.project.runtime_cfg.vars.to_dict()
        toplevel_conf = self._find_first(
            [c.get(k, {}) for k in ["dbt-osmosis", "dbt_osmosis"]], lambda v: bool(v), {}
        )
        return toplevel_conf.get("yaml_settings", {})

    def read_catalog(self) -> CatalogResults | None:
        """カタログ ファイルが存在する場合はそれを読み取ります。"""
        logger.debug(":mag: Checking if catalog is already loaded => %s", bool(self._catalog))
        if not self._catalog:
            from dbt_osmosis.core.introspection import _generate_catalog, _load_catalog

            catalog = _load_catalog(self.settings)
            if not catalog and self.settings.create_catalog_if_not_exists:
                logger.info(
                    ":bookmark_tabs: No existing catalog found, generating new catalog.json."
                )
                catalog = _generate_catalog(self.project)
            self._catalog = catalog
        return self._catalog

    def _find_first(
        self, coll: t.Iterable[t.Any], predicate: t.Callable[[t.Any], bool], default: t.Any = None
    ) -> t.Any:
        """述語を満たすコンテナー内の最初の項目を検索します。"""
        for item in coll:
            if predicate(item):
                return item
        return default

    def __post_init__(self) -> None:
        logger.debug(":green_book: Running post-init for YamlRefactorContext.")
        if EMPTY_STRING not in self.placeholders:
            self.placeholders = (EMPTY_STRING, *self.placeholders)
        # ここでyaml_handlerを初期化します
        from dbt_osmosis.core.schema.parser import create_yaml_instance

        self.yaml_handler = create_yaml_instance()
        for setting, val in self.yaml_settings.items():
            setattr(self.yaml_handler, setting, val)
        self.pool._max_workers = self.project.runtime_cfg.threads
        logger.info(
            ":notebook: Osmosis ThreadPoolExecutor max_workers synced with dbt => %s",
            self.pool._max_workers,
        )
