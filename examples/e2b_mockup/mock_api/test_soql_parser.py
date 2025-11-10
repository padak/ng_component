"""Tests for the SOQL parser."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from soql_parser import parse_soql, SOQLParseError


def test_simple_select():
    """Test basic SELECT * FROM query."""
    soql = "SELECT * FROM Lead"
    sql = parse_soql(soql)
    print(f"✓ Simple SELECT: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "SELECT * FROM leads" == sql


def test_select_with_fields():
    """Test SELECT with specific fields."""
    soql = "SELECT Id, Name, Email FROM Lead"
    sql = parse_soql(soql)
    print(f"✓ SELECT with fields: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "SELECT Id, Name, Email FROM leads" == sql


def test_select_with_where():
    """Test SELECT with WHERE clause."""
    soql = "SELECT * FROM Lead WHERE Status='Open'"
    sql = parse_soql(soql)
    print(f"✓ SELECT with WHERE: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "WHERE Status='Open'" in sql


def test_select_with_date_comparison():
    """Test SELECT with date comparison."""
    soql = "SELECT * FROM Lead WHERE CreatedDate > '2024-01-01'"
    sql = parse_soql(soql)
    print(f"✓ SELECT with date: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "WHERE CreatedDate > '2024-01-01'" in sql


def test_select_with_and():
    """Test SELECT with AND operator."""
    soql = "SELECT * FROM Lead WHERE Status='Open' AND CreatedDate > '2024-01-01'"
    sql = parse_soql(soql)
    print(f"✓ SELECT with AND: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "Status='Open' AND CreatedDate > '2024-01-01'" in sql


def test_select_with_order_by():
    """Test SELECT with ORDER BY clause."""
    soql = "SELECT * FROM Lead ORDER BY CreatedDate DESC"
    sql = parse_soql(soql)
    print(f"✓ SELECT with ORDER BY: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "ORDER BY CreatedDate DESC" in sql


def test_select_with_limit():
    """Test SELECT with LIMIT clause."""
    soql = "SELECT * FROM Lead LIMIT 100"
    sql = parse_soql(soql)
    print(f"✓ SELECT with LIMIT: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "LIMIT 100" in sql


def test_complex_query():
    """Test complex query with all clauses."""
    soql = "SELECT Id, Name, Status FROM Lead WHERE Status='Open' ORDER BY CreatedDate DESC LIMIT 50"
    sql = parse_soql(soql)
    print(f"✓ Complex query: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "SELECT Id, Name, Status FROM leads" in sql
    assert "WHERE Status='Open'" in sql
    assert "ORDER BY CreatedDate DESC" in sql
    assert "LIMIT 50" in sql


def test_opportunity_query():
    """Test query on Opportunity object."""
    soql = "SELECT * FROM Opportunity WHERE Amount > 10000"
    sql = parse_soql(soql)
    print(f"✓ Opportunity query: {soql}")
    print(f"  → SQL: {sql}\n")
    assert "FROM opportunities" in sql


def test_invalid_sobject():
    """Test error handling for invalid SObject."""
    soql = "SELECT * FROM UnknownObject"
    try:
        parse_soql(soql)
        assert False, "Should have raised SOQLParseError"
    except SOQLParseError as e:
        print(f"✓ Invalid SObject handled: {str(e)}\n")


def test_missing_select():
    """Test error handling for missing SELECT."""
    soql = "FROM Lead"
    try:
        parse_soql(soql)
        assert False, "Should have raised SOQLParseError"
    except SOQLParseError as e:
        print(f"✓ Missing SELECT handled: {str(e)}\n")


def test_missing_from():
    """Test error handling for missing FROM."""
    soql = "SELECT * WHERE Status='Open'"
    try:
        parse_soql(soql)
        assert False, "Should have raised SOQLParseError"
    except SOQLParseError as e:
        print(f"✓ Missing FROM handled: {str(e)}\n")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("SOQL Parser Tests")
    print("=" * 60 + "\n")

    tests = [
        test_simple_select,
        test_select_with_fields,
        test_select_with_where,
        test_select_with_date_comparison,
        test_select_with_and,
        test_select_with_order_by,
        test_select_with_limit,
        test_complex_query,
        test_opportunity_query,
        test_invalid_sobject,
        test_missing_select,
        test_missing_from,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {str(e)}\n")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
