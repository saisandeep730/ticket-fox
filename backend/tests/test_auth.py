from app.auth import _mock_uid


def test_mock_uid_stability():
    token_1 = "bearer_sample_user_token_abc"
    token_2 = "bearer_sample_user_token_abc"
    token_diff = "bearer_sample_user_token_xyz"

    uid_1 = _mock_uid(token_1)
    uid_2 = _mock_uid(token_2)
    uid_diff = _mock_uid(token_diff)

    assert uid_1.startswith("mock_")
    # Deterministic: the same token must map to the same UID across restarts.
    assert uid_1 == uid_2
    assert uid_1 != uid_diff
