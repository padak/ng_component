-- Salesforce Mock Database Schema

-- Campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    Id VARCHAR PRIMARY KEY,
    Name VARCHAR NOT NULL,
    Type VARCHAR,
    Status VARCHAR,
    StartDate DATE,
    Budget DECIMAL(10, 2),
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    Id VARCHAR PRIMARY KEY,
    FirstName VARCHAR,
    LastName VARCHAR NOT NULL,
    Email VARCHAR,
    Company VARCHAR,
    Status VARCHAR,
    Source VARCHAR,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CampaignId VARCHAR,
    FOREIGN KEY (CampaignId) REFERENCES campaigns(Id)
);

-- Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    Id VARCHAR PRIMARY KEY,
    Name VARCHAR NOT NULL,
    Industry VARCHAR,
    Revenue DECIMAL(12, 2),
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Opportunities table
CREATE TABLE IF NOT EXISTS opportunities (
    Id VARCHAR PRIMARY KEY,
    Name VARCHAR NOT NULL,
    Amount DECIMAL(12, 2),
    StageName VARCHAR,
    LeadId VARCHAR,
    CloseDate DATE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (LeadId) REFERENCES leads(Id)
);
