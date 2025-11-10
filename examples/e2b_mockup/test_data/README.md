# Salesforce Test Data

Realistic Salesforce test dataset in CSV format with DuckDB database schema for testing queries, joins, aggregations, and analytics.

## Overview

This dataset simulates a typical B2B SaaS sales pipeline with:
- **100 Leads** - Potential customers from various sources and campaigns
- **15 Campaigns** - Marketing campaigns across different channels
- **40 Opportunities** - Active and closed sales deals
- **25 Accounts** - Customer companies across 5 industries

## Data Model

```
campaigns (15 records)
    ├── Id (Primary Key)
    ├── Name, Type, Status
    ├── StartDate, Budget
    └── CreatedDate

leads (100 records)
    ├── Id (Primary Key)
    ├── FirstName, LastName, Email
    ├── Company, Status, Source
    ├── CreatedDate
    └── CampaignId (Foreign Key → campaigns.Id)

opportunities (40 records)
    ├── Id (Primary Key)
    ├── Name, Amount, StageName
    ├── CloseDate, CreatedDate
    └── LeadId (Foreign Key → leads.Id)

accounts (25 records)
    ├── Id (Primary Key)
    ├── Name, Industry, Revenue
    └── CreatedDate
```

## Quick Start

### Prerequisites

- Python 3.7+
- DuckDB (`pip install duckdb`)

### Setup Database

```bash
cd examples/e2b_mockup/test_data
python3 setup.py
```

This will:
1. Create `salesforce.duckdb` database
2. Execute `schema.sql` to create tables
3. Import all CSV files from `seeds/` directory
4. Display summary statistics and data integrity checks

### Using the Database

#### Python

```python
import duckdb

conn = duckdb.connect('salesforce.duckdb')

# Query leads by status
leads_df = conn.execute("""
    SELECT Status, COUNT(*) as count
    FROM leads
    GROUP BY Status
""").fetchdf()
print(leads_df)

# Analyze campaign performance
campaign_performance = conn.execute("""
    SELECT
        c.Name,
        c.Type,
        COUNT(l.Id) as leads_generated,
        c.Budget,
        ROUND(c.Budget / NULLIF(COUNT(l.Id), 0), 2) as cost_per_lead
    FROM campaigns c
    LEFT JOIN leads l ON c.Id = l.CampaignId
    GROUP BY c.Id, c.Name, c.Type, c.Budget
    ORDER BY leads_generated DESC
""").fetchdf()
print(campaign_performance)

conn.close()
```

#### DuckDB CLI

```bash
duckdb salesforce.duckdb
```

```sql
-- Show all tables
.tables

-- Explore leads
SELECT * FROM leads LIMIT 10;

-- Campaign ROI analysis
SELECT
    c.Name,
    c.Budget,
    COUNT(DISTINCT l.Id) as total_leads,
    COUNT(DISTINCT o.Id) as total_opportunities,
    SUM(o.Amount) as pipeline_value
FROM campaigns c
LEFT JOIN leads l ON c.Id = l.CampaignId
LEFT JOIN opportunities o ON l.Id = o.LeadId
GROUP BY c.Id, c.Name, c.Budget
ORDER BY pipeline_value DESC;
```

## Data Characteristics

### Leads (100 records)
- **Status Distribution**: New (25%), Working (25%), Qualified (40%), Unqualified (10%)
- **Sources**: Web (40%), Referral (20%), Partner (20%), Conference (15%), Webinar (5%)
- **Date Range**: Created over past 90 days (Aug 15 - Nov 8, 2024)
- **Campaign Attribution**: All leads linked to marketing campaigns

### Campaigns (15 records)
- **Types**: Email (5), Webinar (4), Conference (3), Partner (2), Event (1)
- **Status**: Active (9), Completed (6)
- **Budget Range**: $8,000 - $50,000
- **Total Budget**: $342,000

### Opportunities (40 records)
- **Stages**:
  - Prospecting (8 opps)
  - Qualification (8 opps)
  - Proposal (8 opps)
  - Negotiation (8 opps)
  - Closed Won (6 opps)
  - Closed Lost (2 opps)
- **Amount Range**: $75,000 - $510,000
- **Total Pipeline**: ~$9.4M
- **Win Rate**: 75% (6 won out of 8 closed)
- **Average Deal Size**: $235,000

### Accounts (25 records)
- **Industries**: Technology (6), Healthcare (5), Finance (5), Retail (5), Manufacturing (4)
- **Revenue Range**: $5.6M - $89M
- **Total Revenue**: ~$573M

## Sample Queries

### Lead Conversion Analysis
```sql
SELECT
    l.Status,
    COUNT(l.Id) as lead_count,
    COUNT(o.Id) as opp_count,
    ROUND(COUNT(o.Id) * 100.0 / COUNT(l.Id), 2) as conversion_rate
FROM leads l
LEFT JOIN opportunities o ON l.Id = o.LeadId
GROUP BY l.Status
ORDER BY lead_count DESC;
```

### Campaign Performance
```sql
SELECT
    c.Name,
    c.Type,
    c.Budget,
    COUNT(l.Id) as leads,
    COUNT(o.Id) as opportunities,
    SUM(CASE WHEN o.StageName = 'Closed Won' THEN o.Amount ELSE 0 END) as won_revenue,
    ROUND(c.Budget / NULLIF(COUNT(l.Id), 0), 2) as cost_per_lead
FROM campaigns c
LEFT JOIN leads l ON c.Id = l.CampaignId
LEFT JOIN opportunities o ON l.Id = o.LeadId
GROUP BY c.Id, c.Name, c.Type, c.Budget
ORDER BY won_revenue DESC;
```

### Sales Pipeline by Stage
```sql
SELECT
    StageName,
    COUNT(*) as count,
    SUM(Amount) as total_amount,
    AVG(Amount) as avg_amount,
    MIN(Amount) as min_amount,
    MAX(Amount) as max_amount
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
    END;
```

### Monthly Lead Trends
```sql
SELECT
    DATE_TRUNC('month', CreatedDate) as month,
    Source,
    COUNT(*) as lead_count
FROM leads
GROUP BY DATE_TRUNC('month', CreatedDate), Source
ORDER BY month, lead_count DESC;
```

### Top Companies by Pipeline Value
```sql
SELECT
    l.Company,
    COUNT(DISTINCT l.Id) as total_leads,
    COUNT(DISTINCT o.Id) as total_opportunities,
    SUM(o.Amount) as pipeline_value,
    MAX(o.Amount) as largest_deal
FROM leads l
LEFT JOIN opportunities o ON l.Id = o.LeadId
GROUP BY l.Company
HAVING SUM(o.Amount) > 0
ORDER BY pipeline_value DESC
LIMIT 10;
```

### Account Industry Analysis
```sql
SELECT
    Industry,
    COUNT(*) as account_count,
    AVG(Revenue) as avg_revenue,
    MIN(Revenue) as min_revenue,
    MAX(Revenue) as max_revenue,
    SUM(Revenue) as total_revenue
FROM accounts
GROUP BY Industry
ORDER BY total_revenue DESC;
```

## File Structure

```
test_data/
├── README.md              # This file
├── schema.sql            # DuckDB table definitions
├── setup.py              # Database setup script
├── salesforce.duckdb     # Generated database (after setup)
└── seeds/
    ├── campaigns.csv     # 15 marketing campaigns
    ├── leads.csv         # 100 lead records
    ├── opportunities.csv # 40 opportunity records
    └── accounts.csv      # 25 account records
```

## Use Cases

This dataset is ideal for:

1. **Testing SQL Queries**: Practice joins, aggregations, window functions
2. **Data Analysis**: Calculate conversion rates, pipeline metrics, campaign ROI
3. **Dashboard Development**: Build sales analytics dashboards
4. **ETL Testing**: Test data transformation pipelines
5. **API Development**: Mock Salesforce API responses
6. **ML Training**: Train lead scoring or opportunity prediction models
7. **Performance Testing**: Benchmark query performance and optimization

## Data Quality Notes

- All foreign key relationships are valid (no orphaned records)
- Dates are realistic and follow logical progression
- Names and emails are varied and realistic
- Pipeline stages follow standard sales methodology
- Campaign budgets and opportunity amounts are realistic for B2B SaaS
- 40% of leads have associated opportunities (realistic conversion rate)

## Extending the Dataset

To add more data:

1. Edit CSV files in `seeds/` directory
2. Maintain ID format (e.g., LED001, CMP001)
3. Ensure foreign keys reference valid records
4. Run `python3 setup.py` to recreate database

## License

This is test data for development and testing purposes. Feel free to modify and extend as needed.
