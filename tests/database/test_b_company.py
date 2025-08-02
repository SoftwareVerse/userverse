from app.database.company import Company


def test_create_company_one(test_session, test_company_data):
    company_data = test_company_data["company_one"]
    company = Company.create(test_session, **company_data)
    assert company["email"] == company_data["email"]


def test_create_company_two(test_session, test_company_data):
    company_data = test_company_data["company_two"]
    company = Company.create(test_session, **company_data)
    assert company["email"] == company_data["email"]
    assert company["name"] == company_data["name"]
    assert company["industry"] == company_data["industry"]


def test_update_company_one(test_session, test_company_data):
    company_data = test_company_data["company_one"]
    company_update_data = test_company_data["update_company_one"]
    created_company = Company.create(
        test_session, email=company_data["email"], name=company_data["name"]
    )
    updated_company = Company.update(
        test_session, created_company["id"], **company_update_data
    )
    assert updated_company["name"] == company_update_data["name"]
    assert updated_company["industry"] == company_update_data["industry"]
    assert updated_company["description"] == company_update_data["description"]
    assert updated_company["phone_number"] == company_update_data["phone_number"]


def test_add_company_address(test_session, test_company_data):
    company_data = test_company_data["company_one"]
    company_address_data = test_company_data["json_field"]
    created_company = Company.create(
        test_session, email=company_data["email"], name=company_data["name"]
    )
    updated_company = Company.update_json_field(
        test_session,
        created_company["id"],
        company_address_data["column"],
        company_address_data["key"],
        company_address_data["value"],
    )

    # Updated company: {'id': 1, 'name': 'Company One', 'description': None, 'industry': None, 'email': 'company.one@email.com', 'phone_number': None, '_created_at': datetime.datetime(2025, 5, 10, 18, 46, 55), '_updated_at': datetime.datetime(2025, 5, 10, 18, 46, 55), '_closed_at': None, 'primary_meta_data': {'address': {'street': '123 Main St', 'city': 'Johannesburg', 'state': 'Gauteng', 'postal_code': '2000', 'country': 'South Africa'}}, 'secondary_meta_data': {}}
    assert (
        updated_company["primary_meta_data"]["address"]["street"]
        == company_address_data["value"]["street"]
    )
    assert (
        updated_company["primary_meta_data"]["address"]["city"]
        == company_address_data["value"]["city"]
    )
    assert (
        updated_company["primary_meta_data"]["address"]["state"]
        == company_address_data["value"]["state"]
    )
    assert (
        updated_company["primary_meta_data"]["address"]["postal_code"]
        == company_address_data["value"]["postal_code"]
    )
    assert (
        updated_company["primary_meta_data"]["address"]["country"]
        == company_address_data["value"]["country"]
    )
