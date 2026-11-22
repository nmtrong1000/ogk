import re

from app.modules.webfilter.catalog_data import catalog_rows


def test_catalog_has_at_least_200_unique_valid_domain_rows():
    rows = catalog_rows()
    pattern = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
    assert len(rows) >= 200
    assert len({domain for domain, _category in rows}) == len(rows)
    assert all(pattern.fullmatch(domain) for domain, _category in rows)
