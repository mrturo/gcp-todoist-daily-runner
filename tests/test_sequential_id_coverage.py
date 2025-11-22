"""Additional coverage tests for sequential_id validation edge cases."""

from src.main import _validate_sequential_id


def test_validate_sequential_id_with_malformed_id_parts():
    """Test that malformed IDs that cause ValueError/IndexError are handled."""
    all_ids = {"A01-01-00"}

    # Test with ID that has non-numeric parts (causes ValueError)
    assert _validate_sequential_id("AXX-01-00", all_ids) is False
    assert _validate_sequential_id("A01-XX-00", all_ids) is False

    # Test with ID that has empty parts (causes IndexError)
    assert _validate_sequential_id("A-01-00", all_ids) is False

    # Test with ID that has malformed structure
    assert _validate_sequential_id("01-01-00", all_ids) is False  # No letter prefix
