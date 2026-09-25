from app.dedupe import fingerprint, normalize


def test_normalize_ignores_case_spaces_and_line_breaks():
    assert normalize("  Hi,  we need\na WEBSITE ") == "hi, we need a website"


def test_same_message_with_trivial_differences_has_same_fingerprint():
    a = fingerprint("Raj@Acme.com", "Hi, we need a website by next month.")
    b = fingerprint("  raj@acme.com ", "Hi,  we need a website\nby next month.")
    assert a == b


def test_edited_message_has_different_fingerprint():
    a = fingerprint("raj@acme.com", "we need a website")
    b = fingerprint("raj@acme.com", "we need a website!")
    assert a != b


def test_different_sender_has_different_fingerprint():
    assert fingerprint("a@x.com", "hello") != fingerprint("b@x.com", "hello")


def test_sender_and_body_cannot_be_shifted_to_collide():
    assert fingerprint("a|b", "c") != fingerprint("a", "b|c")
