from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from sqlalchemy.dialects import postgresql
from app.repositories.contacts import ContactRepository
from app.schemas.filters import ContactFilterParams, AttributeListParams
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata

repo = ContactRepository()
filters = ContactFilterParams()
params = AttributeListParams()

stmt = select(func.distinct(func.unnest(Company.industries)));
company_alias = aliased(Company, name='company_attribute')
contact_meta_alias = aliased(ContactMetadata, name='contact_meta_attribute')
company_meta_alias = aliased(CompanyMetadata, name='company_meta_attribute')
stmt = stmt.select_from(Contact)
stmt = stmt.outerjoin(company_alias, Contact.company_id == company_alias.uuid)
stmt = stmt.outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
stmt = stmt.outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)
stmt = repo.apply_filters(stmt, filters, company_alias, company_meta_alias, contact_meta_alias)
stmt = repo.apply_search_terms(stmt, params.search or filters.search, company_alias, company_meta_alias, contact_meta_alias)
stmt = stmt.limit(params.limit).offset(params.offset)
compiled = stmt.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True})
print(compiled)
