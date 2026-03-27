-- Regional Sharding & Data Sovereignty Constraints (CockroachDB)
-- This script configures row-level data residency for the Super App.

-- 1. Configure Localities (Assumes EKS/Cockroach-Operator setup)
-- Localities are typically passed at startup: 
-- --locality=region=us-east-1,az=us-east-1a

-- 2. Partitioning: user_pii (Strict Data Sovereignty)
ALTER TABLE IF EXISTS user_pii 
PARTITION BY LIST (region) (
    PARTITION p_us VALUES IN ('USA'),
    PARTITION p_eu VALUES IN ('EUROPE'),
    PARTITION p_in VALUES IN ('INDIA'),
    PARTITION p_global VALUES IN ('LATAM', 'AFRICAS', 'GLOBAL') -- Default catch-all
);

-- 3. Zone Configuration (Pinning to HSM/Region hardware)
-- These constraints tell CockroachDB's replication engine exactly where to place the replicas.
ALTER PARTITION p_us OF TABLE user_pii CONFIGURE ZONE USING constraints = '[+region=us-east-1]';
ALTER PARTITION p_eu OF TABLE user_pii CONFIGURE ZONE USING constraints = '[+region=eu-west-1]';
ALTER PARTITION p_in OF TABLE user_pii CONFIGURE ZONE USING constraints = '[+region=ap-south-1]';

-- 4. Duplicate Tables (Reference Data)
-- Small, read-heavy tables should be replicated globally for low-latency joins.
-- Ex: FX Rates, Country Codes.
ALTER TABLE IF EXISTS currencies CONFIGURE ZONE USING num_replicas = 9; -- Replicate to all regions

-- 5. Regional by Row: Wallets (Performance Sharding)
-- While not strictly required for sovereignty (money is often 'global'), 
-- we shard wallets by region to minimize cross-region write contention on transaction hot-paths.
ALTER TABLE IF EXISTS wallets
PARTITION BY LIST (region) (
    PARTITION w_us VALUES IN ('USA'),
    PARTITION w_eu VALUES IN ('EUROPE'),
    PARTITION w_in VALUES IN ('INDIA')
);

ALTER PARTITION w_us OF TABLE wallets CONFIGURE ZONE USING lease_preferences = '[[+region=us-east-1]]';
ALTER PARTITION w_eu OF TABLE wallets CONFIGURE ZONE USING lease_preferences = '[[+region=eu-west-1]]';
ALTER PARTITION w_in OF TABLE wallets CONFIGURE ZONE USING lease_preferences = '[[+region=ap-south-1]]';

-- 6. Indices (Must be partitioned to avoid cross-region lookup overhead)
-- (Automatically handled by CockroachDB for partitioned primary keys)
