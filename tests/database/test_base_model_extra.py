import pytest

from app.database.base_model import BaseModel, RecordNotFoundError
from app.database.company import Company
from app.database.user import User


def test_to_dict_handles_none_and_model_lists(test_session, test_user_data):
    user_one = User.create(test_session, **test_user_data["create_user"])
    user_two = User.create(
        test_session,
        email="two@example.com",
        password="secret",
        first_name="Two",
    )

    records = test_session.query(User).order_by(User.id).all()

    assert BaseModel.to_dict(None) == {}
    assert BaseModel.to_dict(records)[0]["id"] == user_one["id"]
    assert BaseModel.to_dict(records)[1]["id"] == user_two["id"]


def test_to_dict_falls_back_to_convert_datetime_for_plain_values():
    assert BaseModel.to_dict({"nested": "value"}) == {"nested": "value"}


def test_update_missing_record_raises_record_not_found(test_session):
    with pytest.raises(RecordNotFoundError):
        User.update(test_session, 999, first_name="missing")


def test_update_by_filters_missing_record_raises_value_error(test_session):
    with pytest.raises(ValueError, match="User with filters"):
        User.update_by_filters(
            test_session, filters={"email": "missing@example.com"}, first_name="missing"
        )


def test_delete_missing_record_raises_record_not_found(test_session):
    with pytest.raises(RecordNotFoundError):
        User.delete(test_session, 999)


def test_delete_by_filters_missing_record_raises_value_error(test_session):
    with pytest.raises(ValueError, match="User with filters"):
        User.delete_by_filters(test_session, filters={"email": "missing@example.com"})


def test_bulk_create_creates_multiple_companies(test_session):
    result = Company.bulk_create(
        test_session,
        [
            {"email": "bulk-one@example.com", "name": "Bulk One"},
            {"email": "bulk-two@example.com", "name": "Bulk Two"},
        ],
    )

    assert result == {"message": "2 records added successfully"}
    assert test_session.query(Company).count() == 2


def test_update_json_field_initializes_none_json_column(test_session, test_user_data):
    created = User.create(test_session, **test_user_data["create_user"])
    user = test_session.query(User).filter_by(id=created["id"]).one()
    user.primary_meta_data = None
    test_session.commit()

    updated = User.update_json_field(
        test_session,
        created["id"],
        "primary_meta_data",
        "status",
        "Active",
    )

    assert updated["primary_meta_data"]["status"] == "Active"


def test_update_json_field_rejects_non_dict_columns(test_session, test_user_data):
    created = User.create(test_session, **test_user_data["create_user"])

    with pytest.raises(ValueError, match="Column email is not a JSON field."):
        User.update_json_field(test_session, created["id"], "email", "status", "Active")


def test_bulk_update_json_field_updates_multiple_keys(test_session, test_user_data):
    created = User.create(test_session, **test_user_data["create_user"])

    updated = User.bulk_update_json_field(
        test_session,
        created["id"],
        "primary_meta_data",
        {"status": "Active", "source": "tests"},
    )

    assert updated["primary_meta_data"]["status"] == "Active"
    assert updated["primary_meta_data"]["source"] == "tests"


def test_bulk_update_json_field_initializes_none_json_column(
    test_session, test_user_data
):
    created = User.create(test_session, **test_user_data["create_user"])
    user = test_session.query(User).filter_by(id=created["id"]).one()
    user.secondary_meta_data = None
    test_session.commit()

    updated = User.bulk_update_json_field(
        test_session,
        created["id"],
        "secondary_meta_data",
        {"source": "tests"},
    )

    assert updated["secondary_meta_data"]["source"] == "tests"


def test_bulk_update_json_field_rejects_invalid_column(test_session, test_user_data):
    created = User.create(test_session, **test_user_data["create_user"])

    with pytest.raises(
        ValueError, match="Column 'missing_column' does not exist on the model."
    ):
        User.bulk_update_json_field(
            test_session,
            created["id"],
            "missing_column",
            {"source": "tests"},
        )


def test_bulk_update_json_field_rejects_non_dict_column(test_session, test_user_data):
    created = User.create(test_session, **test_user_data["create_user"])

    with pytest.raises(ValueError, match="Column 'email' is not a JSON/dict field."):
        User.bulk_update_json_field(
            test_session,
            created["id"],
            "email",
            {"source": "tests"},
        )


def test_bulk_update_json_field_missing_record_raises_record_not_found(test_session):
    with pytest.raises(RecordNotFoundError):
        User.bulk_update_json_field(
            test_session,
            999,
            "primary_meta_data",
            {"source": "tests"},
        )
