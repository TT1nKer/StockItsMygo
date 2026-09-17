import pytest

from auth import hash_password, register_user, verify_password
from web_dashboard import app, get_stock_links


@pytest.fixture()
def client():
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    with app.test_client() as test_client:
        yield test_client


def test_login_page_is_available(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Stock Dashboard" in response.data


def test_dashboard_redirects_anonymous_users(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_update_endpoint_requires_authentication(client):
    response = client.post("/api/update")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"

    status_response = client.get("/api/update/status")
    assert status_response.status_code == 401


def test_invalid_json_login_is_a_client_error_not_a_server_error(client):
    response = client.post("/login", data="not-json", content_type="application/json")
    assert response.status_code == 401


def test_password_hash_round_trip():
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_registration_validates_before_opening_database():
    success, message, user_id = register_user("ab", "short", "invalid")
    assert not success
    assert message == "Invalid invitation code"
    assert user_id is None


def test_market_links_support_us_and_china_symbols():
    assert "yahoo" in get_stock_links("AAPL")
    assert "eastmoney" in get_stock_links("sh600519")
    assert "eastmoney" in get_stock_links("sz000001")
