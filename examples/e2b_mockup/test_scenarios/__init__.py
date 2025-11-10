"""
Test Scenarios Package

This package contains test scenarios for validating agent capabilities
when interacting with the Salesforce Mock API.

Scenarios:
- scenario_1_simple_query: Basic time-based lead query
- scenario_2_object_discovery: Object metadata discovery
- scenario_3_field_discovery: Field schema introspection
- scenario_4_filtered_query: Complex JOIN with filters
- scenario_5_aggregation: Analytics query with GROUP BY

Usage:
    # Run all scenarios
    python run_all_scenarios.py

    # Run individual scenario
    python scenario_1_simple_query.py

    # Run specific scenario from runner
    python run_all_scenarios.py --scenario 1
"""

__version__ = "1.0.0"
__all__ = [
    "scenario_1_simple_query",
    "scenario_2_object_discovery",
    "scenario_3_field_discovery",
    "scenario_4_filtered_query",
    "scenario_5_aggregation",
    "run_all_scenarios",
]
