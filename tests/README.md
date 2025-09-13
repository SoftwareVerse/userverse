# Userverse Testing

    -   To run the first suite 
    ```bash
    export TEST_ENVIRONMENT=true
    ```

## Database

Unit testing for db models

```bash

# User Model testing, tests/database/test_b_company.py
(userverse) $: pytest -v tests/database/test_a_user.py -s

# company tests
(userverse) $: pytest -v tests/database/test_b_company.py -s

# role tests
(userverse) $: pytest -v tests/database/test_c_role.py -s

# association
(userverse) $: pytest -v tests/database/test_e_association.py -s

```


## 📡 HTTP Integration Testing

### ⚙️ Setup

Ensure your environment uses a **dedicated test database** to avoid conflicts with development data.

```bash
# Activate testing environment flag
export TEST_ENVIRONMENT=True
```

---

### 🌲 Directory Structure (3 Levels)

```
tests/http/
├── a_user/
│   ├── test_a_create_user_api.py
│   ├── test_b_user_login_api.py
│   ├── test_c_get_user.py
│   ├── test_d_update_user_api.py
│   ├── test_e_password_reset_request.py
│   └── test_f_password_otp_verify.py
├── b_company/
│   ├── test_a_create_company.py
│   ├── test_b_get_company.py
│   └── test_c_update_company.py
├── c_company_roles/
│   ├── test_d_create_role.py
│   ├── test_e_update_role.py
│   ├── test_f_delete_role.py
│   └── test_g_get_roles.py
├── d_company_users/
│   ├── test_h_get_company_users.py
│   ├── test_i_get_user_companies.py
│   ├── test_j_add_user_to_company.py
│   └── test_k_remove_user_from_company.py
├── test_main.py
├── test_security.py
└── conftest.py
```

---

### 🚀 Running Tests

#### 🧪 Main & Security
```bash
pytest -v tests/http/test_main.py
pytest -v tests/http/test_security.py
```

#### 👤 User APIs
```bash
pytest -v tests/http/a_user/test_a_create_user_api.py
pytest -v tests/http/a_user/test_b_user_login_api.py
pytest -v tests/http/a_user/test_c_get_user.py
pytest -v tests/http/a_user/test_d_update_user_api.py
pytest -v tests/http/a_user/test_e_password_reset_request.py
pytest -v tests/http/a_user/test_f_password_otp_verify.py
```

#### 🏢 Company APIs
```bash
pytest -v tests/http/b_company/test_a_create_company.py
pytest -v tests/http/b_company/test_b_get_company.py
pytest -v tests/http/b_company/test_c_update_company.py
```

#### 🧑‍💼 Company Role APIs
```bash
pytest -v tests/http/c_company_roles/test_d_create_role.py
pytest -v tests/http/c_company_roles/test_e_update_role.py
pytest -v tests/http/c_company_roles/test_f_delete_role.py
pytest -v tests/http/c_company_roles/test_g_get_roles.py
```

#### 👥 Company User APIs
```bash
pytest -v tests/http/d_company_users/test_h_get_company_users.py
pytest -v tests/http/d_company_users/test_i_get_user_companies.py
pytest -v tests/http/d_company_users/test_j_add_user_to_company.py
pytest -v tests/http/d_company_users/test_k_remove_user_from_company.py
```



## 🧰 Utility Testing

### 📂 Directory Structure

```
tests/utils/
├── basic_auth.py
├── config/
│   ├── test_cors.py
│   ├── test_database_config.py
│   └── test_environment_manager.py
├── email/
│   ├── __init__.py
│   ├── test_renderer.py
│   └── test_sender.py
└── __init__.py
```

---

### 🚀 Running Utility Tests

#### 🔐 Basic Auth Utilities
```bash
pytest -v tests/utils/basic_auth.py
```

#### ⚙️ Configuration Tests
```bash
pytest -v tests/utils/config/test_cors.py
pytest -v tests/utils/config/test_database_config.py
pytest -v tests/utils/config/test_environment_manager.py
```

#### 📧 Email Utilities
```bash
pytest -v tests/utils/email/test_renderer.py
pytest -v tests/utils/email/test_sender.py
```