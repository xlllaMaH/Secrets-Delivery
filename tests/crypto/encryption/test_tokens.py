from src.crypto.encryption.tokens import generate_token


def test_generate_token_is_random():
    assert generate_token() != generate_token()


def test_generate_token_is_url_safe_and_has_expected_length():
    token = generate_token()

    assert len(token) == 22
    assert all(char.isalnum() or char in "-_" for char in token)
