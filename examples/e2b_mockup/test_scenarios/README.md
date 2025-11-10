# Test Scenarios - Agent Capability Testing

This directory contains comprehensive test scenarios designed to demonstrate and measure agent capabilities when interacting with the Salesforce Mock API. These scenarios simulate real-world user requests and validate that the agent can correctly interpret intent, generate appropriate queries, and return accurate results.

## Overview

The test scenarios cover five key aspects of agent intelligence:

1. **Simple Query** - Basic time-based filtering
2. **Object Discovery** - API exploration and metadata retrieval
3. **Field Discovery** - Schema introspection
4. **Complex Filtering** - Multi-table JOINs with conditions
5. **Aggregation** - Analytics queries with GROUP BY

## Prerequisites

Before running the test scenarios, ensure you have:

1. **Mock API Server Running**
   ```bash
   cd ../mock_api
   python main.py
   ```
   The server should be accessible at `http://localhost:8000`

2. **Environment Variables Set**
   ```bash
   export SF_API_KEY=test-api-key-123
   export SF_API_URL=http://localhost:8000  # Optional, defaults to localhost:8000
   ```

3. **Test Data Loaded**
   ```bash
   cd ../test_data
   python setup.py
   ```
   This creates the DuckDB database with sample Salesforce data.

4. **Dependencies Installed**
   ```bash
   cd ..
   pip install -r requirements.txt
   ```

## Test Scenarios

### Scenario 1: Simple Lead Query

**File:** `scenario_1_simple_query.py`

**User Prompt:** "Get all leads from the last 30 days"

**What It Tests:**
- Basic SOQL query generation
- Date filtering with time-based conditions
- Proper field selection
- Date comparison logic

**Expected Behavior:**
- Generates `SELECT` query with `WHERE CreatedDate >= DATE` clause
- Returns only leads created in the last 30 days
- Includes core fields: Id, Name, Email, Company, Status, CreatedDate

**Success Criteria:**
- Query executes without errors
- Results contain proper date filtering
- All required fields present in results
- Date comparison logic is correct

**Run:**
```bash
python scenario_1_simple_query.py
```

---

### Scenario 2: Object Discovery

**File:** `scenario_2_object_discovery.py`

**User Prompt:** "What objects are available in Salesforce?"

**What It Tests:**
- API exploration capabilities
- Understanding of metadata endpoints
- Result parsing and display

**Expected Behavior:**
- Calls `list_objects()` API method
- Parses response correctly
- Displays all available objects

**Success Criteria:**
- Successfully retrieves object list
- Returns all 4 test objects (Lead, Campaign, Account, Opportunity)
- No API errors
- Results displayed in readable format

**Run:**
```bash
python scenario_2_object_discovery.py
```

---

### Scenario 3: Field Discovery

**File:** `scenario_3_field_discovery.py`

**User Prompt:** "What fields does the Lead object have?"

**What It Tests:**
- Schema introspection
- Field metadata retrieval
- Understanding of object structure

**Expected Behavior:**
- Calls `get_fields('Lead')` API method
- Retrieves complete field schema
- Shows field names, types, and attributes

**Success Criteria:**
- Successfully retrieves field schema
- Returns complete field definitions
- All expected fields present (Id, Name, Email, Company, Status, etc.)
- Field types and metadata displayed correctly

**Run:**
```bash
python scenario_3_field_discovery.py
```

---

### Scenario 4: Complex Filtered Query

**File:** `scenario_4_filtered_query.py`

**User Prompt:** "Get qualified leads from webinar campaigns"

**What It Tests:**
- Multi-table JOIN generation
- Complex WHERE conditions
- Understanding of relationships between objects
- Multiple filter criteria

**Expected Behavior:**
- Generates SOQL with `INNER JOIN` between Lead and Campaign
- Applies multiple WHERE conditions:
  - `Lead.Status = 'Qualified'`
  - `Campaign.Type = 'Webinar'`
- Returns combined data from both objects

**Success Criteria:**
- Query includes proper JOIN syntax
- Multiple filter conditions applied correctly
- Results include fields from both objects
- Only matching records returned
- No orphaned or invalid joins

**Run:**
```bash
python scenario_4_filtered_query.py
```

---

### Scenario 5: Aggregation Query

**File:** `scenario_5_aggregation.py`

**User Prompt:** "Which campaign has the most leads?"

**What It Tests:**
- Analytics query generation
- Aggregation functions (COUNT)
- GROUP BY logic
- ORDER BY for ranking

**Expected Behavior:**
- Generates SOQL with `COUNT()` aggregation
- Includes `GROUP BY Campaign`
- Uses `ORDER BY COUNT DESC` to rank results
- Returns campaign with highest lead count

**Success Criteria:**
- Query uses aggregation correctly
- Results grouped by campaign
- Results ordered by lead count (descending)
- Top campaign identified correctly
- Count values are accurate

**Run:**
```bash
python scenario_5_aggregation.py
```

## Running All Scenarios

Use the test runner to execute all scenarios in sequence:

```bash
python run_all_scenarios.py
```

### Runner Options

**Run all scenarios:**
```bash
python run_all_scenarios.py
```

**Run with verbose output:**
```bash
python run_all_scenarios.py --verbose
```

**Run specific scenario:**
```bash
python run_all_scenarios.py --scenario 1  # Run only scenario 1
python run_all_scenarios.py -s 2          # Run only scenario 2
```

**Skip prerequisite checks:**
```bash
python run_all_scenarios.py --skip-checks  # Not recommended
```

### Understanding the Report

The test runner generates a comprehensive report showing:

1. **Overall Status**
   - Success rate (% of passed scenarios)
   - Total execution time
   - Pass/fail count

2. **Scenario Results Table**
   - Individual scenario status
   - Execution time per scenario
   - Error counts

3. **Failed Scenarios Details**
   - Specific errors for each failure
   - Warnings and potential issues

4. **Performance Metrics**
   - API call timing
   - Query execution time
   - Record counts
   - Other scenario-specific metrics

5. **JSON Report**
   - Detailed report saved to `test_report_YYYYMMDD_HHMMSS.json`
   - Machine-readable format for analysis
   - Includes all metrics and results

## Success Metrics

Each scenario measures different aspects of agent capability:

### Functional Success
- Query generates correctly
- Results match expected criteria
- No API errors
- Data integrity maintained

### Performance Metrics
- **Execution Time** - Total time to complete scenario
- **API Time** - Time spent in API calls
- **Query Time** - Database query execution time
- **Record Count** - Number of results returned

### Quality Indicators
- **Error Count** - Number of errors encountered
- **Warning Count** - Non-fatal issues detected
- **Validation Pass Rate** - % of validation checks passed

## Adding New Scenarios

To add a new test scenario:

1. **Create scenario file** (e.g., `scenario_6_your_test.py`)
   ```python
   #!/usr/bin/env python3
   """
   Scenario 6: Your Test Name
   Description of what this tests.
   """

   class Scenario6YourTest:
       def __init__(self):
           self.name = "Scenario 6: Your Test"
           self.description = "Brief description"
           self.user_prompt = "User's natural language request"
           self.success = False
           self.errors = []
           self.warnings = []
           self.metrics = {}

       def run(self) -> Dict[str, Any]:
           """Execute the test scenario"""
           # Your test logic here
           pass

       def _validate_results(self):
           """Validate results against success criteria"""
           pass

       def _generate_report(self) -> Dict[str, Any]:
           """Generate test report"""
           return {
               'scenario': self.name,
               'user_prompt': self.user_prompt,
               'success': self.success,
               'errors': self.errors,
               'warnings': self.warnings,
               'metrics': self.metrics,
           }
   ```

2. **Add to runner** (`run_all_scenarios.py`)
   ```python
   SCENARIOS = [
       # ... existing scenarios ...
       {
           'module': 'scenario_6_your_test',
           'class': 'Scenario6YourTest',
           'name': 'Your Test Name',
           'description': 'Brief description',
       },
   ]
   ```

3. **Document in README** (this file)
   - Add scenario description
   - Document user prompt
   - List success criteria
   - Add run instructions

## Interpreting Results

### Pass (✓ PASS)
The scenario completed successfully with no errors. The agent:
- Correctly interpreted the user prompt
- Generated appropriate queries
- Returned accurate results
- Passed all validation checks

### Fail (✗ FAIL)
The scenario encountered errors. Common causes:
- **API Connection Issues** - Mock server not running
- **Query Errors** - Invalid SOQL syntax
- **Validation Failures** - Results don't match expected criteria
- **Missing Data** - Required test data not present

Check the error details in the report for specific issues.

### Warnings (⚠)
Non-fatal issues that don't cause failure but may indicate:
- Missing optional data
- Performance concerns
- Edge cases encountered
- Data quality issues

## Troubleshooting

### "Failed to connect to Salesforce API"
**Cause:** Mock API server not running
**Solution:** Start the server with `cd ../mock_api && python main.py`

### "API key is required"
**Cause:** SF_API_KEY environment variable not set
**Solution:** Run `export SF_API_KEY=test-api-key-123`

### "Database not found"
**Cause:** Test database not created
**Solution:** Run `cd ../test_data && python setup.py`

### "No results returned"
**Cause:** Test data may not match query criteria
**Solution:** This is often expected with time-based queries. Check warnings.

### Import errors
**Cause:** Missing dependencies
**Solution:** Run `pip install -r ../requirements.txt`

## Best Practices

1. **Run Prerequisites First**
   - Always start mock API server
   - Set environment variables
   - Load test data

2. **Check Reports**
   - Review detailed JSON reports for metrics
   - Track performance over time
   - Identify patterns in failures

3. **Iterative Testing**
   - Run single scenarios during development
   - Use `--scenario N` flag for focused testing
   - Run full suite before commits

4. **Monitor Performance**
   - Track execution times
   - Watch for performance regressions
   - Optimize slow queries

5. **Update Test Data**
   - Keep test data realistic
   - Cover edge cases
   - Document data dependencies

## Future Enhancements

Potential scenarios to add:

- **Update Operations** - Testing data modification
- **Delete Operations** - Testing record deletion
- **Relationship Traversal** - Testing complex object relationships
- **Error Handling** - Testing graceful failure scenarios
- **Batch Operations** - Testing bulk data operations
- **Concurrent Queries** - Testing race conditions
- **Security/Permissions** - Testing access control

## Related Documentation

- **Mock API Documentation** - `../mock_api/README.md`
- **Test Data Documentation** - `../test_data/README.md`
- **Salesforce Driver** - `../salesforce_driver/README.md`

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the Mock API logs
3. Examine the detailed JSON reports
4. Verify test data is properly loaded

## License

Part of the ng_component project.
