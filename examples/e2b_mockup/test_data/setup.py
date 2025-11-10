#!/usr/bin/env python3
"""
Salesforce Test Data Setup Script
Creates DuckDB database, imports schema, and loads CSV seed data.
"""

import duckdb
import os
from pathlib import Path
from datetime import datetime

def setup_database():
    """Create and populate the Salesforce test database"""

    # Define paths
    script_dir = Path(__file__).parent
    db_path = script_dir / "salesforce.duckdb"
    schema_path = script_dir / "schema.sql"
    seeds_dir = script_dir / "seeds"

    # Remove existing database if it exists
    if db_path.exists():
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)

    # Create new database connection
    print(f"\nCreating new database: {db_path}")
    conn = duckdb.connect(str(db_path))

    try:
        # Execute schema
        print(f"\nExecuting schema from: {schema_path}")
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        conn.execute(schema_sql)
        print("Schema created successfully")

        # Import CSV files
        csv_files = {
            'campaigns': seeds_dir / 'campaigns.csv',
            'accounts': seeds_dir / 'accounts.csv',
            'leads': seeds_dir / 'leads.csv',
            'opportunities': seeds_dir / 'opportunities.csv'
        }

        print("\n" + "="*60)
        print("IMPORTING CSV DATA")
        print("="*60)

        for table_name, csv_path in csv_files.items():
            if not csv_path.exists():
                print(f"WARNING: {csv_path} not found, skipping...")
                continue

            print(f"\nImporting {table_name} from {csv_path.name}...")

            # Import CSV data
            conn.execute(f"""
                COPY {table_name} FROM '{csv_path}'
                (HEADER, DELIMITER ',', QUOTE '"')
            """)

            # Get row count
            result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            count = result[0]
            print(f"  ✓ Imported {count} rows into {table_name}")

        # Print summary statistics
        print("\n" + "="*60)
        print("DATABASE SUMMARY")
        print("="*60)

        # Campaigns summary
        print("\nCAMPAIGNS:")
        campaigns_stats = conn.execute("""
            SELECT
                Status,
                COUNT(*) as count,
                SUM(Budget) as total_budget
            FROM campaigns
            GROUP BY Status
            ORDER BY Status
        """).fetchall()

        for status, count, budget in campaigns_stats:
            print(f"  {status}: {count} campaigns, ${budget:,.2f} total budget")

        # Leads summary
        print("\nLEADS:")
        leads_stats = conn.execute("""
            SELECT
                Status,
                COUNT(*) as count
            FROM leads
            GROUP BY Status
            ORDER BY Status
        """).fetchall()

        for status, count in leads_stats:
            print(f"  {status}: {count} leads")

        # Leads by source
        print("\n  By Source:")
        source_stats = conn.execute("""
            SELECT
                Source,
                COUNT(*) as count
            FROM leads
            GROUP BY Source
            ORDER BY count DESC
        """).fetchall()

        for source, count in source_stats:
            print(f"    {source}: {count} leads")

        # Opportunities summary
        print("\nOPPORTUNITIES:")
        opp_stats = conn.execute("""
            SELECT
                StageName,
                COUNT(*) as count,
                SUM(Amount) as total_amount,
                AVG(Amount) as avg_amount
            FROM opportunities
            GROUP BY StageName
            ORDER BY
                CASE StageName
                    WHEN 'Prospecting' THEN 1
                    WHEN 'Qualification' THEN 2
                    WHEN 'Proposal' THEN 3
                    WHEN 'Negotiation' THEN 4
                    WHEN 'Closed Won' THEN 5
                    WHEN 'Closed Lost' THEN 6
                END
        """).fetchall()

        for stage, count, total, avg in opp_stats:
            print(f"  {stage}: {count} opps, ${total:,.2f} total, ${avg:,.2f} avg")

        # Total opportunity value
        total_opp = conn.execute("""
            SELECT SUM(Amount) FROM opportunities
        """).fetchone()[0]

        print(f"\n  Total Pipeline Value: ${total_opp:,.2f}")

        # Win rate
        win_stats = conn.execute("""
            SELECT
                SUM(CASE WHEN StageName = 'Closed Won' THEN 1 ELSE 0 END) as won,
                SUM(CASE WHEN StageName IN ('Closed Won', 'Closed Lost') THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN StageName = 'Closed Won' THEN Amount ELSE 0 END) as won_amount
            FROM opportunities
        """).fetchone()

        won, closed, won_amount = win_stats
        win_rate = (won / closed * 100) if closed > 0 else 0
        print(f"  Win Rate: {win_rate:.1f}% ({won}/{closed} closed opportunities)")
        print(f"  Won Amount: ${won_amount:,.2f}")

        # Accounts summary
        print("\nACCOUNTS:")
        account_stats = conn.execute("""
            SELECT
                Industry,
                COUNT(*) as count,
                AVG(Revenue) as avg_revenue
            FROM accounts
            GROUP BY Industry
            ORDER BY count DESC
        """).fetchall()

        for industry, count, avg_rev in account_stats:
            print(f"  {industry}: {count} accounts, ${avg_rev:,.2f} avg revenue")

        # Data integrity checks
        print("\n" + "="*60)
        print("DATA INTEGRITY CHECKS")
        print("="*60)

        # Check for orphaned leads
        orphaned_leads = conn.execute("""
            SELECT COUNT(*)
            FROM leads
            WHERE CampaignId IS NOT NULL
            AND CampaignId NOT IN (SELECT Id FROM campaigns)
        """).fetchone()[0]

        print(f"\nOrphaned leads (invalid CampaignId): {orphaned_leads}")

        # Check for orphaned opportunities
        orphaned_opps = conn.execute("""
            SELECT COUNT(*)
            FROM opportunities
            WHERE LeadId IS NOT NULL
            AND LeadId NOT IN (SELECT Id FROM leads)
        """).fetchone()[0]

        print(f"Orphaned opportunities (invalid LeadId): {orphaned_opps}")

        # Check for leads with opportunities
        leads_with_opps = conn.execute("""
            SELECT COUNT(DISTINCT LeadId)
            FROM opportunities
            WHERE LeadId IS NOT NULL
        """).fetchone()[0]

        total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        conversion_rate = (leads_with_opps / total_leads * 100) if total_leads > 0 else 0

        print(f"\nLeads with opportunities: {leads_with_opps}/{total_leads} ({conversion_rate:.1f}%)")

        # Sample queries
        print("\n" + "="*60)
        print("SAMPLE QUERIES")
        print("="*60)

        print("\nTop 5 Campaigns by Lead Count:")
        top_campaigns = conn.execute("""
            SELECT
                c.Name,
                c.Type,
                COUNT(l.Id) as lead_count,
                c.Budget
            FROM campaigns c
            LEFT JOIN leads l ON c.Id = l.CampaignId
            GROUP BY c.Id, c.Name, c.Type, c.Budget
            ORDER BY lead_count DESC
            LIMIT 5
        """).fetchall()

        for name, type_, count, budget in top_campaigns:
            print(f"  {name} ({type_}): {count} leads, ${budget:,.2f} budget")

        print("\nTop 5 Opportunities by Amount:")
        top_opps = conn.execute("""
            SELECT
                o.Name,
                o.Amount,
                o.StageName,
                l.Company
            FROM opportunities o
            LEFT JOIN leads l ON o.LeadId = l.Id
            ORDER BY o.Amount DESC
            LIMIT 5
        """).fetchall()

        for name, amount, stage, company in top_opps:
            company_name = company if company else "N/A"
            print(f"  {name}: ${amount:,.2f} ({stage}) - {company_name}")

        print("\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print(f"\nDatabase created: {db_path}")
        print(f"Database size: {db_path.stat().st_size / 1024:.2f} KB")
        print(f"\nTo query the database:")
        print(f"  python3 -c 'import duckdb; conn = duckdb.connect(\"{db_path}\"); print(conn.execute(\"SELECT * FROM leads LIMIT 5\").fetchdf())'")
        print(f"\nOr use DuckDB CLI:")
        print(f"  duckdb {db_path}")

    except Exception as e:
        print(f"\nERROR: {e}")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    print("="*60)
    print("SALESFORCE TEST DATA SETUP")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    setup_database()

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
