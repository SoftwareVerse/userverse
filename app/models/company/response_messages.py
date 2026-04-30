from enum import Enum


class CompanyResponseMessages(str, Enum):
    # Company creation
    COMPANY_CREATED = "Company has been created successfully."
    COMPANY_CREATION_FAILED = "Unable to create company. Please try again."
    COMPANY_ALREADY_EXISTS = "A company with the provided details already exists."

    # Company retrieval
    COMPANY_NOT_FOUND = "No company found matching the provided criteria."
    COMPANY_FOUND = "Company details retrieved successfully."
    UNAUTHORIZED_COMPANY_ACCESS = (
        "Access denied. You are not authorized to access this company."
    )
    COMPANY_ID_OR_EMAIL_REQUIRED = (
        "Please provide either a company ID or an email address."
    )

    # Company update
    COMPANY_UPDATED = "Company information updated successfully."
    COMPANY_UPDATE_FAILED = "Failed to update company. Please check the provided data."

    # Company deletion
    COMPANY_DELETED = "Company has been deleted successfully."
    COMPANY_DELETION_FAILED = "Unable to delete company. Please try again later."


class CompanyUserResponseMessages(str, Enum):
    # Company users
    GET_COMPANY_USERS = "Company users retrieved successfully."
    GET_USER_COMPANIES = "Associated companies retrieved successfully."

    # Add user
    ADD_USER_SUCCESS = "User has been successfully added to the company."
    ADD_USER_FAILED = "Failed to add user to the company. Please verify the input."
    ADD_EXISTING_USER_FAILED = "User is already linked to company."

    # Remove user
    REMOVE_USER_SUCCESS = "User has been successfully removed from the company."
    REMOVE_USER_FAILED = "Failed to remove user from the company. Try again later."
    SUPER_ADMIN_REMOVE_FORBIDDEN = "You cannot remove super admin from company."
    USER_ALREADY_REMOVED = "User has already been removed from company."


class CompanyRoleResponseMessages(str, Enum):
    # Role creation
    ROLE_CREATION_SUCCESS = "Role has been created successfully."
    ROLE_CREATION_FORBIDDEN = "You are not allowed to create roles."
    ROLE_CREATION_FAILED = (
        "Unable to create role. Please verify the data and try again."
    )

    # Role retrieval
    ROLE_GET_SUCCESS = "Roles retrieved successfully."
    ROLE_NOT_FOUND = "No role found with the given identifier."

    # Role deletion
    ROLE_DELETED = "Role has been deleted successfully."
    ROLE_DELETION_FAILED = "Failed to delete the role. Please try again later."

    # Role update
    ROLE_UPDATED = "Role has been updated successfully."
    ROLE_UPDATE_FAILED = "Failed to update the role. Ensure the data is valid."

    # Role existence
    ROLE_ALREADY_EXISTS = "A role with the same name already exists."
