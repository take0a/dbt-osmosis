# pyright: reportPrivateImportUsage=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportUnknownVariableType=false

from dbt_osmosis.core.schema.parser import create_yaml_instance


def test_create_yaml_instance_settings():
    """
    create_yaml_instance が、カスタム インデントを使用して構成された 
    YAML オブジェクトを返すことを簡単に確認します。
    """
    y = create_yaml_instance(indent_mapping=4, indent_sequence=2, indent_offset=0)
    assert y.map_indent == 4
    assert y.sequence_indent == 2
    assert y.sequence_dash_offset == 0
    assert y.width == 100  # default
    assert y.preserve_quotes is False
