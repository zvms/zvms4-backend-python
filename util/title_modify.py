import re


def modify_title_automatically(title: str):
    """
    Automatically modifies a title to ensure it meets the specified requirements:
    1. Contains only Chinese, Latin Characters, numbers, spaces, slashes, and dots.
    2. ASCII letters are wrapped with spaces if inserted between Chinese characters.

    Args:
        title (str): The input title string.

    Returns:
        str: The modified title string.
    """
    modified_title = title

    # Requirement 2: Ensure ASCII letters are wrapped with spaces if between Chinese characters
    # Add space before ASCII char if preceded by Chinese
    modified_title = re.sub(r"([\u4e00-\u9fa5])([a-zA-Z0-9])", r"\1 \2", modified_title)
    # Add space after ASCII char if followed by Chinese
    modified_title = re.sub(r"([a-zA-Z0-9])([\u4e00-\u9fa5])", r"\1 \2", modified_title)

    # Requirement 1: Filter out invalid characters
    # Allow Chinese, Latin Characters, numbers, spaces, slashes, dashes (en dash, em dash, hyphen), and dots
    # The regex for allowed characters is based on your provided validation regex.
    # Note: \u2013 is en dash, \u2014 is em dash. '-' is hyphen.
    allowed_chars_regex = r"[^\u4e00-\u9fa5\u2013\u2014a-zA-Z0-9 /.-]"
    modified_title = re.sub(allowed_chars_regex, "", modified_title)

    # Clean up any extra spaces that might have been introduced or accumulated
    modified_title = re.sub(r"\s+", " ", modified_title).strip()

    return modified_title


# --- Example Usage ---
if __name__ == "__main__":
    test_titles = [
        "这是一个Pythontitle",
        "Python是一个很棒的语言",
        "Title with numbers 123和汉字",
        "Title-with/slashes.and.dots",
        "Title_with_underscore",  # Will be cleaned
        "中English文",
        "中文English",
        "English中文",
        "abc中文def",
        "中文abc",
        "abc中文",
        "Title with invalid character!",
        "Title with space   and multiple spaces",
        "This is an_invalid-character.",
        "中文123英文456",
        "123中文456英文",
        "中-文",  # With a hyphen already
    ]

    for title in test_titles:
        modified_title = modify_title_automatically(title)
        print(f"Original: '{title}'")
        print(f"Modified: '{modified_title}'\n")

        # You can add the validation checks here to see if the modified title passes
        # The validation functions from your prompt:
        def validate_character_set(name):
            if not re.match(r"^[-\u4e00-\u9fa5\u2013-\u2014a-zA-Z0-9 /.-]+$", name):
                return (
                    False,
                    "Should only appear in Chinese, Latin Characters, numbers, spaces, slashes, dashes (including en dash and em dash), and dots",
                )
            return True, "Valid character set"

        def validate_spacing(name):
            if re.search(r"[\u4e00-\u9fa5][a-zA-Z0-9]", name) or re.search(
                r"[a-zA-Z0-9][\u4e00-\u9fa5]", name
            ):
                return (
                    False,
                    "ASCII letters should be wrapped with spaces if inserted between Chinese characters",
                )
            return True, "Valid spacing"

        is_char_set_valid, char_set_msg = validate_character_set(modified_title)
        is_spacing_valid, spacing_msg = validate_spacing(modified_title)

        print(f"  Validation (Char Set): {is_char_set_valid} - {char_set_msg}")
        print(f"  Validation (Spacing): {is_spacing_valid} - {spacing_msg}")
        print("-" * 30)
