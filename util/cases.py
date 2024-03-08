import re


def kebab_case_to_camel_case(s: str) -> str:
    result = "".join([word.capitalize() for word in s.split("-")])
    # the first word should be lowercase
    return result[0].lower() + result[1:]


def kebab_case_to_snake_case(s: str) -> str:
    return "_".join([word.lower() for word in s.split("-")])


def camel_case_to_kebab_case(s: str) -> str:
    return "-".join([word.lower() for word in re.findall(r"[A-Z][a-z]*", s)])
