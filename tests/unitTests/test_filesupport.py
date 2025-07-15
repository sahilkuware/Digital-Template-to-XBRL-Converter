from mireport.filesupport import is_valid_filename, zipSafeString


def test_is_valid_filename_valid_cases() -> None:
    assert is_valid_filename("test.txt")
    assert is_valid_filename("example_file.doc")
    assert is_valid_filename("file.name.ext")


def test_is_valid_filename_dot_and_dotdot() -> None:
    assert not is_valid_filename(".")
    assert not is_valid_filename("..")


def test_is_valid_filename_reserved_names() -> None:
    assert not is_valid_filename("CON")
    assert not is_valid_filename("con")
    assert not is_valid_filename("AuX")
    for i in range(1, 10):
        assert not is_valid_filename(f"COM{i}")
        assert not is_valid_filename(f"LPT{i}")


def test_is_valid_filename_invalid_characters() -> None:
    assert not is_valid_filename("my|file.txt")
    assert not is_valid_filename("bad:file")
    assert not is_valid_filename("invalid*name.doc")


def test_is_valid_filename_valid_misc_characters() -> None:
    assert is_valid_filename("valid-file_name.txt")
    assert is_valid_filename("another.valid_file-name.md")


def test_zipSafeString_valid_input() -> None:
    assert zipSafeString("good filename.txt") == "good_filename.txt"
    assert zipSafeString("normal_name.doc") == "normal_name.doc"


def test_zipSafeString_whitespace_normalization() -> None:
    assert zipSafeString("some    file   name.txt") == "some_file_name.txt"


def test_zipSafeString_invalid_characters_replacement() -> None:
    assert zipSafeString("bad/file:name*here.txt") == "bad_file_name_here.txt"
    assert zipSafeString("weird#name?.ext") == "weird_name_.ext"


def test_zipSafeString_reserved_fallback() -> None:
    assert zipSafeString("CON") == "fallback"


def test_zipSafeString_empty_input() -> None:
    assert zipSafeString("") == "fallback"


def test_zipSafeString_custom_fallback() -> None:
    assert zipSafeString("CON", fallback="default") == "default"
