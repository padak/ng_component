import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

# Initialize client
client = SalesforceClient(
    api_url='http://localhost:8000',
    api_key='test_key_12345'
)

try:
    # Query all leads with available fields
    results = client.query("SELECT Id, FirstName, LastName, Email, Company, Status, Source, CreatedDate FROM Lead ORDER BY CreatedDate DESC")

    # Format and return as JSON
    output = {
        'count': len(results),
        'data': results
    }
    print(json.dumps(output, indent=2))

except Exception as e:
    error = {'error': str(e)}
    print(json.dumps(error, indent=2))
