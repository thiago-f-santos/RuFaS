import pytest

from RUFAS.biophysical.field.field.field_data import FieldData


def test_field_data_southern_hemisphere_latitude():
    """Tests that negative latitude in Southern Hemisphere sets absolute_latitude and preserves latitude."""
    fd = FieldData(name="brazil_field", latitude=-22.5)
    assert fd.latitude == -22.5
    assert fd.absolute_latitude == 22.5
    assert fd.dormancy_threshold is not None


def test_field_data_legacy_absolute_latitude():
    """Tests that legacy initialization with only absolute_latitude sets latitude equal to absolute_latitude."""
    fd = FieldData(name="legacy_field", absolute_latitude=43.5)
    assert fd.latitude == 43.5
    assert fd.absolute_latitude == 43.5


def test_field_data_default_latitude():
    """Tests default latitude when neither is explicitly provided."""
    fd = FieldData(name="default_field")
    assert fd.latitude == 43.5
    assert fd.absolute_latitude == 43.5


def test_field_data_both_provided():
    """Tests that when both are provided, latitude takes precedence for sign and absolute_latitude is sanitized."""
    fd = FieldData(name="both_field", latitude=-15.78, absolute_latitude=15.78)
    assert fd.latitude == -15.78
    assert fd.absolute_latitude == 15.78
