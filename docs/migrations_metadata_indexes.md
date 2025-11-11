# Metadata Index Migration

The contacts API now relies on additional database indexes to speed up metadata-driven list and count queries:
- `contacts_metadata.city`, `contacts_metadata.state`, `contacts_metadata.country`
- `companies_metadata.company_name_for_emails`, `companies_metadata.city`, `companies_metadata.state`, `companies_metadata.country`

## Upgrade steps
1. Generate a migration that captures the new indexes:
   ```bash
   alembic revision --autogenerate -m "Add metadata indexes"
   ```
2. Inspect the generated script and ensure the `op.create_index` calls match the schema changes above.
3. Apply the migration to your environment:
   ```bash
   alembic upgrade head
   ```

> Note: On large datasets, creating these indexes can take several minutes. Schedule the migration during a low-traffic window if you are running against production data.
