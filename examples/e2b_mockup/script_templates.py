"""
Script Templates for Salesforce Operations

This module provides pre-built script templates for common Salesforce operations.
These templates simulate what an AI agent would generate when handling user requests.

Each template is a function that returns executable Python code as a string,
configured with the appropriate API credentials and parameters.

Templates include:
- Getting recent leads (by date range)
- Getting campaign with associated leads
- Getting leads by status
- Getting all leads
- Custom queries

In a production system, these templates would be used as examples for an LLM
to generate custom scripts based on user intent.
"""

from datetime import datetime, timedelta
from typing import Optional


class ScriptTemplates:
    """
    Collection of script templates for common Salesforce operations.

    All templates return Python code as strings that can be executed in an E2B sandbox.
    The scripts are pre-configured with necessary imports, client initialization,
    and error handling.
    """

    @staticmethod
    def get_recent_leads(
        api_url: str,
        api_key: str,
        days: int = 30,
        limit: Optional[int] = None
    ) -> str:
        """
        Generate script to get leads created in the last N days.

        Args:
            api_url: Salesforce API URL (should be sandbox-accessible)
            api_key: API authentication key
            days: Number of days to look back (default: 30)
            limit: Maximum number of records to return (optional)

        Returns:
            Python script as a string
        """
        # Calculate the date threshold
        date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        limit_clause = f"LIMIT {limit}" if limit else ""

        script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json
from datetime import datetime, timedelta

print("Fetching leads from the last {days} days...")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

# Calculate date threshold
date_threshold = '{date_threshold}'
print(f"Date threshold: {{date_threshold}}")

# Query for recent leads
query = """
SELECT Id, Name, Email, Company, Status, CreatedDate
FROM Lead
WHERE CreatedDate >= {{date_threshold}}
ORDER BY CreatedDate DESC
{limit_clause}
""".strip()

print(f"Executing query: {{query}}")

try:
    leads = client.query(query)

    print(f"\\nFound {{len(leads)}} leads created since {{date_threshold}}")

    # Display summary
    if leads:
        print("\\nSample leads:")
        for i, lead in enumerate(leads[:5], 1):
            print(f"  {{i}}. {{lead.get('Name', 'N/A')}} - {{lead.get('Company', 'N/A')}} ({{lead.get('Status', 'N/A')}})")

        if len(leads) > 5:
            print(f"  ... and {{len(leads) - 5}} more")

    # Return results as JSON
    result = {{
        'count': len(leads),
        'date_threshold': date_threshold,
        'leads': leads
    }}

    print("\\n" + "="*50)
    print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e),
        'query': query
    }}
    print(json.dumps(error_result, indent=2))
'''
        return script

    @staticmethod
    def get_campaign_with_leads(
        api_url: str,
        api_key: str,
        campaign_name: str
    ) -> str:
        """
        Generate script to get a campaign and all its associated leads.

        This demonstrates a more complex query involving joins between
        Campaign and Lead objects through CampaignMember.

        Args:
            api_url: Salesforce API URL
            api_key: API authentication key
            campaign_name: Name of the campaign to retrieve

        Returns:
            Python script as a string
        """
        script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

print("Fetching campaign: '{campaign_name}' with associated leads...")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

try:
    # First, find the campaign
    campaign_query = """
    SELECT Id, Name, Status, StartDate, EndDate, NumberOfLeads, NumberOfContacts
    FROM Campaign
    WHERE Name LIKE '%{campaign_name}%'
    LIMIT 1
    """

    print(f"Finding campaign: {{campaign_query}}")
    campaigns = client.query(campaign_query)

    if not campaigns:
        result = {{
            'error': 'Campaign not found',
            'campaign_name': '{campaign_name}'
        }}
        print(json.dumps(result, indent=2))
    else:
        campaign = campaigns[0]
        campaign_id = campaign['Id']

        print(f"Found campaign: {{campaign['Name']}} (ID: {{campaign_id}})")

        # Get campaign members (leads associated with this campaign)
        members_query = f"""
        SELECT Id, LeadId, Status, CreatedDate
        FROM CampaignMember
        WHERE CampaignId = '{{campaign_id}}'
        """

        print(f"\\nFetching campaign members...")
        members = client.query(members_query)

        print(f"Found {{len(members)}} campaign members")

        # Get lead details for each member
        if members:
            lead_ids = [m['LeadId'] for m in members if m.get('LeadId')]

            if lead_ids:
                # Build IN clause with lead IDs
                lead_ids_str = "', '".join(lead_ids)
                leads_query = f"""
                SELECT Id, Name, Email, Company, Status
                FROM Lead
                WHERE Id IN ('{{lead_ids_str}}')
                """

                print(f"Fetching lead details for {{len(lead_ids)}} leads...")
                leads = client.query(leads_query)
            else:
                leads = []
        else:
            leads = []

        # Combine results
        result = {{
            'campaign': campaign,
            'member_count': len(members),
            'lead_count': len(leads),
            'leads': leads
        }}

        print(f"\\nCampaign: {{campaign['Name']}}")
        print(f"Status: {{campaign.get('Status', 'N/A')}}")
        print(f"Total Members: {{len(members)}}")
        print(f"Total Leads: {{len(leads)}}")

        if leads:
            print("\\nSample leads:")
            for i, lead in enumerate(leads[:5], 1):
                print(f"  {{i}}. {{lead.get('Name', 'N/A')}} - {{lead.get('Company', 'N/A')}}")

        print("\\n" + "="*50)
        print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e),
        'campaign_name': '{campaign_name}'
    }}
    print(json.dumps(error_result, indent=2))
'''
        return script

    @staticmethod
    def get_leads_by_status(
        api_url: str,
        api_key: str,
        status: str,
        limit: Optional[int] = 100
    ) -> str:
        """
        Generate script to get leads filtered by status.

        Args:
            api_url: Salesforce API URL
            api_key: API authentication key
            status: Lead status to filter by (e.g., 'New', 'Qualified', 'Working')
            limit: Maximum number of records to return

        Returns:
            Python script as a string
        """
        limit_clause = f"LIMIT {limit}" if limit else ""

        script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

print("Fetching leads with status: '{status}'...")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

try:
    # Query leads by status
    query = """
    SELECT Id, Name, Email, Company, Status, CreatedDate, LastModifiedDate
    FROM Lead
    WHERE Status = '{status}'
    ORDER BY CreatedDate DESC
    {limit_clause}
    """

    print(f"Executing query: {{query}}")

    leads = client.query(query)

    print(f"\\nFound {{len(leads)}} leads with status '{status}'")

    # Group by company
    companies = {{}}
    for lead in leads:
        company = lead.get('Company', 'Unknown')
        if company not in companies:
            companies[company] = []
        companies[company].append(lead)

    print(f"Across {{len(companies)}} companies")

    # Display summary
    if leads:
        print("\\nTop companies by lead count:")
        sorted_companies = sorted(companies.items(), key=lambda x: len(x[1]), reverse=True)
        for i, (company, company_leads) in enumerate(sorted_companies[:5], 1):
            print(f"  {{i}}. {{company}}: {{len(company_leads)}} leads")

        print("\\nSample leads:")
        for i, lead in enumerate(leads[:5], 1):
            print(f"  {{i}}. {{lead.get('Name', 'N/A')}} - {{lead.get('Company', 'N/A')}} - {{lead.get('Email', 'N/A')}}")

        if len(leads) > 5:
            print(f"  ... and {{len(leads) - 5}} more")

    # Return results
    result = {{
        'status': '{status}',
        'count': len(leads),
        'companies': list(companies.keys()),
        'leads': leads
    }}

    print("\\n" + "="*50)
    print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e),
        'status': '{status}'
    }}
    print(json.dumps(error_result, indent=2))
'''
        return script

    @staticmethod
    def get_all_leads(
        api_url: str,
        api_key: str,
        limit: int = 100
    ) -> str:
        """
        Generate script to get all leads with basic information.

        Args:
            api_url: Salesforce API URL
            api_key: API authentication key
            limit: Maximum number of records to return

        Returns:
            Python script as a string
        """
        script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

print("Fetching all leads (limit: {limit})...")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

try:
    # Query all leads
    query = """
    SELECT Id, Name, Email, Company, Status, CreatedDate
    FROM Lead
    ORDER BY CreatedDate DESC
    LIMIT {limit}
    """

    print(f"Executing query: {{query}}")

    leads = client.query(query)

    print(f"\\nFound {{len(leads)}} leads")

    # Analyze by status
    status_counts = {{}}
    for lead in leads:
        status = lead.get('Status', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\\nBreakdown by status:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {{status}}: {{count}}")

    # Sample leads
    if leads:
        print("\\nSample leads:")
        for i, lead in enumerate(leads[:5], 1):
            print(f"  {{i}}. {{lead.get('Name', 'N/A')}} - {{lead.get('Company', 'N/A')}} ({{lead.get('Status', 'N/A')}})")

        if len(leads) > 5:
            print(f"  ... and {{len(leads) - 5}} more")

    # Return results
    result = {{
        'count': len(leads),
        'status_breakdown': status_counts,
        'leads': leads
    }}

    print("\\n" + "="*50)
    print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e),
        'query': query
    }}
    print(json.dumps(error_result, indent=2))
'''
        return script

    @staticmethod
    def get_lead_count(
        api_url: str,
        api_key: str,
        object_name: str = 'Lead'
    ) -> str:
        """
        Generate script to get total count of records for an object.

        Args:
            api_url: Salesforce API URL
            api_key: API authentication key
            object_name: Name of the Salesforce object

        Returns:
            Python script as a string
        """
        script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

print("Counting {object_name} records...")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

try:
    # Get count
    count = client.get_object_count('{object_name}')

    result = {{
        'object': '{object_name}',
        'count': count
    }}

    print(f"Total {{'{object_name}'}} records: {{count}}")
    print("\\n" + "="*50)
    print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e),
        'object': '{object_name}'
    }}
    print(json.dumps(error_result, indent=2))
'''
        return script

    @staticmethod
    def custom_query(
        api_url: str,
        api_key: str,
        soql_query: str
    ) -> str:
        """
        Generate script to execute a custom SOQL query.

        Args:
            api_url: Salesforce API URL
            api_key: API authentication key
            soql_query: SOQL query to execute

        Returns:
            Python script as a string
        """
        # Escape single quotes in the query
        escaped_query = soql_query.replace("'", "\\'")

        script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

query = """{escaped_query}"""

print(f"Executing custom query: {{query}}")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

try:
    # Execute query
    results = client.query(query)

    print(f"\\nQuery returned {{len(results)}} records")

    # Display sample
    if results:
        print("\\nSample results:")
        for i, record in enumerate(results[:5], 1):
            print(f"  {{i}}. {{record}}")

        if len(results) > 5:
            print(f"  ... and {{len(results) - 5}} more")

    # Return results
    result = {{
        'query': query,
        'count': len(results),
        'records': results
    }}

    print("\\n" + "="*50)
    print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e),
        'query': query
    }}
    print(json.dumps(error_result, indent=2))
'''
        return script

    @staticmethod
    def discover_schema(
        api_url: str,
        api_key: str,
        object_name: Optional[str] = None
    ) -> str:
        """
        Generate script to discover object schemas.

        Args:
            api_url: Salesforce API URL
            api_key: API authentication key
            object_name: Specific object to describe (if None, lists all objects)

        Returns:
            Python script as a string
        """
        if object_name:
            # Describe specific object
            script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

print("Describing object: '{object_name}'...")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

try:
    # Get object schema
    schema = client.get_fields('{object_name}')

    print(f"\\nObject: {{schema.get('name', '{object_name}')}}")
    print(f"Fields: {{len(schema.get('fields', []))}}")

    print("\\nField details:")
    for field in schema.get('fields', []):
        field_type = field.get('type', 'unknown')
        field_name = field.get('name', 'unknown')
        field_label = field.get('label', field_name)
        required = field.get('required', False)
        req_marker = " *" if required else ""
        print(f"  - {{field_name}} ({{field_type}}){{req_marker}}: {{field_label}}")

    result = {{
        'object': '{object_name}',
        'schema': schema
    }}

    print("\\n" + "="*50)
    print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e),
        'object': '{object_name}'
    }}
    print(json.dumps(error_result, indent=2))
'''
        else:
            # List all objects
            script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

print("Discovering available Salesforce objects...")

# Initialize Salesforce client
client = SalesforceClient(
    api_url='{api_url}',
    api_key='{api_key}'
)

try:
    # List all objects
    objects = client.list_objects()

    print(f"\\nFound {{len(objects)}} objects:")
    for i, obj in enumerate(objects, 1):
        print(f"  {{i}}. {{obj}}")

    result = {{
        'count': len(objects),
        'objects': objects
    }}

    print("\\n" + "="*50)
    print(json.dumps(result, indent=2))

except Exception as e:
    error_result = {{
        'error': str(e)
    }}
    print(json.dumps(error_result, indent=2))
'''

        return script


# Example usage and testing
if __name__ == '__main__':
    print("Script Templates - Examples")
    print("="*80)

    # Example 1: Recent leads template
    print("\n1. Recent Leads Template:")
    print("-"*80)
    script = ScriptTemplates.get_recent_leads(
        api_url='http://host.docker.internal:8000',
        api_key='test_key',
        days=30
    )
    print(script[:500] + "...")

    # Example 2: Campaign with leads template
    print("\n\n2. Campaign with Leads Template:")
    print("-"*80)
    script = ScriptTemplates.get_campaign_with_leads(
        api_url='http://host.docker.internal:8000',
        api_key='test_key',
        campaign_name='Summer Campaign'
    )
    print(script[:500] + "...")

    # Example 3: Custom query template
    print("\n\n3. Custom Query Template:")
    print("-"*80)
    script = ScriptTemplates.custom_query(
        api_url='http://host.docker.internal:8000',
        api_key='test_key',
        soql_query="SELECT Id, Name FROM Lead WHERE Email != null LIMIT 10"
    )
    print(script[:500] + "...")
