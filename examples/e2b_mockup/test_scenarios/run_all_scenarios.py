#!/usr/bin/env python3
"""
Test Scenario Runner
Executes all test scenarios and generates a comprehensive report.

This script runs all scenarios in sequence and collects:
- Success/failure status
- Execution times
- Error messages
- Performance metrics
- Overall success rate

Usage:
    python run_all_scenarios.py
    python run_all_scenarios.py --verbose
    python run_all_scenarios.py --scenario 1  # Run only scenario 1
"""

import sys
import os
import argparse
import importlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Define scenarios to run
SCENARIOS = [
    {
        'module': 'scenario_1_simple_query',
        'class': 'Scenario1SimpleQuery',
        'name': 'Simple Lead Query',
        'description': 'Basic time-based query with date filtering',
    },
    {
        'module': 'scenario_2_object_discovery',
        'class': 'Scenario2ObjectDiscovery',
        'name': 'Object Discovery',
        'description': 'Discover available Salesforce objects',
    },
    {
        'module': 'scenario_3_field_discovery',
        'class': 'Scenario3FieldDiscovery',
        'name': 'Field Discovery',
        'description': 'Discover field schema for objects',
    },
    {
        'module': 'scenario_4_filtered_query',
        'class': 'Scenario4FilteredQuery',
        'name': 'Complex Filtered Query',
        'description': 'JOIN query with multiple filter conditions',
    },
    {
        'module': 'scenario_5_aggregation',
        'class': 'Scenario5Aggregation',
        'name': 'Aggregation Query',
        'description': 'Analytics query with GROUP BY and COUNT',
    },
]


class ScenarioRunner:
    """Runs test scenarios and generates reports"""

    def __init__(self, verbose=False, specific_scenario=None):
        self.verbose = verbose
        self.specific_scenario = specific_scenario
        self.results = []
        self.start_time = None
        self.end_time = None

    def run_scenario(self, scenario_def: Dict[str, str]) -> Dict[str, Any]:
        """Run a single scenario"""
        module_name = scenario_def['module']
        class_name = scenario_def['class']

        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Get the scenario class
            scenario_class = getattr(module, class_name)

            # Instantiate and run
            scenario = scenario_class()
            report = scenario.run()

            return report

        except Exception as e:
            return {
                'scenario': scenario_def['name'],
                'success': False,
                'errors': [f"Failed to run scenario: {str(e)}"],
                'warnings': [],
                'metrics': {},
            }

    def run_all(self):
        """Run all scenarios"""
        print("="*80)
        print("SALESFORCE AGENT TEST SCENARIOS")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Running {len(SCENARIOS)} test scenarios...")
        print("="*80 + "\n")

        self.start_time = datetime.now()

        # Filter scenarios if specific one requested
        scenarios_to_run = SCENARIOS
        if self.specific_scenario is not None:
            if 1 <= self.specific_scenario <= len(SCENARIOS):
                scenarios_to_run = [SCENARIOS[self.specific_scenario - 1]]
                print(f"Running only Scenario {self.specific_scenario}\n")
            else:
                print(f"ERROR: Invalid scenario number {self.specific_scenario}")
                print(f"Valid range: 1-{len(SCENARIOS)}\n")
                return

        # Run each scenario
        for i, scenario_def in enumerate(scenarios_to_run, 1):
            print(f"\n{'#'*80}")
            print(f"# SCENARIO {i}/{len(scenarios_to_run)}: {scenario_def['name']}")
            print(f"# {scenario_def['description']}")
            print(f"{'#'*80}\n")

            result = self.run_scenario(scenario_def)
            self.results.append({
                'number': i,
                'definition': scenario_def,
                'result': result,
            })

            # Print quick status
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            print(f"\n{'='*80}")
            print(f"Scenario {i} Status: {status}")
            print(f"{'='*80}\n")

        self.end_time = datetime.now()

        # Generate and print report
        self._print_summary()
        self._save_report()

    def _print_summary(self):
        """Print summary report"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80 + "\n")

        # Calculate statistics
        total_scenarios = len(self.results)
        passed = sum(1 for r in self.results if r['result']['success'])
        failed = total_scenarios - passed
        success_rate = (passed / total_scenarios * 100) if total_scenarios > 0 else 0

        total_time = (self.end_time - self.start_time).total_seconds()

        # Overall status
        print(f"Overall Status: {'✓ ALL PASS' if failed == 0 else '✗ SOME FAILED'}")
        print(f"Success Rate:   {success_rate:.1f}% ({passed}/{total_scenarios} passed)")
        print(f"Total Time:     {total_time:.3f}s")
        print(f"Started:        {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Completed:      {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Scenario results table
        print("Scenario Results:")
        print("-" * 80)
        print(f"{'#':<4} {'Scenario':<30} {'Status':<10} {'Time':<10} {'Errors':<8}")
        print("-" * 80)

        for result_item in self.results:
            scenario_num = result_item['number']
            scenario_name = result_item['definition']['name']
            result = result_item['result']

            status = "✓ PASS" if result['success'] else "✗ FAIL"
            exec_time = result.get('metrics', {}).get('execution_time', 0)
            error_count = len(result.get('errors', []))

            print(f"{scenario_num:<4} {scenario_name:<30} {status:<10} {exec_time:>6.3f}s   {error_count:<8}")

        print("-" * 80)
        print()

        # Failed scenarios details
        if failed > 0:
            print(f"Failed Scenarios ({failed}):")
            print("-" * 80)
            for result_item in self.results:
                if not result_item['result']['success']:
                    scenario_num = result_item['number']
                    scenario_name = result_item['definition']['name']
                    result = result_item['result']

                    print(f"\nScenario {scenario_num}: {scenario_name}")
                    print(f"  Errors:")
                    for error in result.get('errors', []):
                        print(f"    - {error}")

                    if result.get('warnings'):
                        print(f"  Warnings:")
                        for warning in result.get('warnings', []):
                            print(f"    - {warning}")
            print()

        # Performance summary
        print("Performance Metrics:")
        print("-" * 80)
        for result_item in self.results:
            scenario_num = result_item['number']
            scenario_name = result_item['definition']['name']
            metrics = result_item['result'].get('metrics', {})

            print(f"\nScenario {scenario_num}: {scenario_name}")
            for key, value in metrics.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}s")
                else:
                    print(f"  {key}: {value}")

        print("\n" + "="*80 + "\n")

    def _save_report(self):
        """Save detailed report to JSON file"""
        report_file = Path(__file__).parent / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_scenarios': len(self.results),
            'passed': sum(1 for r in self.results if r['result']['success']),
            'failed': sum(1 for r in self.results if not r['result']['success']),
            'success_rate': (sum(1 for r in self.results if r['result']['success']) / len(self.results) * 100) if self.results else 0,
            'total_time': (self.end_time - self.start_time).total_seconds(),
            'scenarios': [
                {
                    'number': item['number'],
                    'name': item['definition']['name'],
                    'description': item['definition']['description'],
                    'success': item['result']['success'],
                    'errors': item['result'].get('errors', []),
                    'warnings': item['result'].get('warnings', []),
                    'metrics': item['result'].get('metrics', {}),
                }
                for item in self.results
            ]
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"Detailed report saved to: {report_file}\n")


def check_prerequisites():
    """Check if prerequisites are met"""
    errors = []

    # Check if SF_API_KEY is set
    if not os.getenv('SF_API_KEY'):
        errors.append(
            "SF_API_KEY environment variable not set. "
            "Please set it before running tests:\n"
            "  export SF_API_KEY=test-api-key-123"
        )

    # Check if mock API server is accessible
    try:
        import requests
        api_url = os.getenv('SF_API_URL', 'http://localhost:8000')
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code != 200:
            errors.append(
                f"Mock API server returned status {response.status_code}. "
                "Please ensure the server is running:\n"
                "  cd mock_api && python main.py"
            )
    except Exception as e:
        errors.append(
            "Cannot connect to mock API server. "
            "Please ensure it's running:\n"
            "  cd mock_api && python main.py\n"
            f"Error: {str(e)}"
        )

    if errors:
        print("="*80)
        print("PREREQUISITE CHECK FAILED")
        print("="*80 + "\n")
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}\n")
        print("="*80 + "\n")
        return False

    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run Salesforce agent test scenarios',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all_scenarios.py              # Run all scenarios
  python run_all_scenarios.py --verbose    # Run with verbose output
  python run_all_scenarios.py --scenario 1 # Run only scenario 1
        """
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--scenario', '-s',
        type=int,
        metavar='N',
        help='Run only scenario N (1-5)'
    )
    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='Skip prerequisite checks (not recommended)'
    )

    args = parser.parse_args()

    # Check prerequisites
    if not args.skip_checks:
        if not check_prerequisites():
            sys.exit(1)

    # Run scenarios
    runner = ScenarioRunner(
        verbose=args.verbose,
        specific_scenario=args.scenario
    )
    runner.run_all()

    # Exit with appropriate code
    failed = sum(1 for r in runner.results if not r['result']['success'])
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
