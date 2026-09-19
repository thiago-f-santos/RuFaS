import json
from pathlib import Path


def test_schema_properties_passo_1():
    schema_path = Path(__file__).parent.parent / "RUFAS" / "input" / "metadata" / "properties" / "default.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # 1. Check config_properties: country and region_code
    config_props = schema["config_properties"]
    assert "country" in config_props, "country must be defined in config_properties"
    assert config_props["country"]["type"] == "string"
    assert config_props["country"]["pattern"] == "^[A-Z]{3}$"
    assert config_props["country"]["default"] == "USA"

    assert "region_code" in config_props, "region_code must be defined in config_properties"
    assert config_props["region_code"]["type"] == "number"
    assert config_props["region_code"]["minimum"] == 1

    assert "FIPS_county_code" in config_props, "FIPS_county_code must remain for retrocompatibility"

    # 2. Check field_properties: latitude
    field_props = schema["field_properties"]
    assert "latitude" in field_props, "latitude must be defined in field_properties"
    assert field_props["latitude"]["type"] == "number"
    assert field_props["latitude"]["minimum"] == -90.0
    assert field_props["latitude"]["maximum"] == 90.0
    assert field_props["latitude"]["default"] == 43.5

    assert "absolute_latitude" in field_props, "absolute_latitude must remain for retrocompatibility"
