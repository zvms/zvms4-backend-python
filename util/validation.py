import re
from datetime import datetime


def validate_activity_name(name: str):
    if not name.strip():
        return False, "Should not be empty"

    if name[0] == " " or name[-1] == " ":
        return False, "Should not have space before or after the string"

    return True, ""


def validate_student_name(name: str):
    """
    Validate student name.
    1. If the name is in Latin characters, it should be capitalized, and separated by space.
    2. If the name is CJK name, it should be in the correct format.
    3. Should not be empty.
    """
    if not name.strip():
        return False, "Should not be empty"

    if name[0] == " " or name[-1] == " ":
        return False, "Should not have space before or after the string"

    # If the name is Chinese name, it should be in the correct format, at most 5 characters and at least 2 characters.
    cjk = re.match(r"^[\u4e00-\u9fa5]{2,5}$", name)

    if not cjk:
        return False, "Should be Chinese name"

    return True, ""


def validate_number(number: str):
    """
    Validate number.
    1. Should be eight digits.
    2. The first four digits reflects the year of registration, which should be in the range grade 1–3, separating school year by Aug 1st.
    3. Then the two digits indicates the class ID, no more than 30.
    4. The last two digits indicates the student ID, no more than 80.
    5. Should not duplicate with existing student number.
    """
    if not re.match(r"^\d{8}$", number):
        return False, "Should be eight digits"

    year = int(number[:4])
    class_id = int(number[4:6])
    student_id = int(number[6:8])

    if datetime.now().month < 8:
        soy = datetime.now().year - 3
        eoy = datetime.now().year - 1
    else:
        soy = datetime.now().year - 2
        eoy = datetime.now().year

    if year < soy or year > eoy:
        return (
            False,
            "The first four digits reflects the year of registration, which should be in the range grade 1–3, separating school year by Aug 1st",
        )

    if class_id < 1 or class_id > 25:
        return False, "Then the two digits indicates the class ID, no more than 25"

    if student_id < 1 or student_id > 60:
        return False, "The last two digits indicates the student ID, no more than 60"

    return True, ""


def validate_past_identity(identity: str):
    """
    Validate past identity.
    1. Should be either name or number.
    2. If the identity is name, it should be in the correct format.
    3. If the identity is number, it should be in the correct format.
    """

    number, numbermsg = validate_number(identity)
    if number:
        return True, ""
    else:
        return False, numbermsg
