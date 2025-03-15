import re
from datetime import datetime

def validate_activity_name(name: str):
    """
    Validate activity name.
    1. Should be only appear in CJK, Latin Characters, numbers, spaces, slashes, and dots.
    2. ASCII letters should be wrapped with spaces if inserted between CJK characters.
    3. Should not be empty.
    4. Should not have space before or after the string.
    5. Should not have CJK punctuation.
    """
    if not name:
        return False

    if name[0] == ' ' or name[-1] == ' ':
        return False

    # Should only contain CJK, Latin Characters, numbers, spaces, slashes, and dots
    if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\uac00-\ud7a3\s\/\.]+$', name):
        return False

    # ASCII letters should be wrapped with spaces if inserted between CJK characters
    if re.search(r'[\u4e00-\u9fff\uac00-\ud7a3][a-zA-Z0-9]', name) or re.search(r'[a-zA-Z0-9][\u4e00-\u9fff]', name):
        return False

    # Should not have CJK punctuation
    if re.search(r'[\u3000-\u303F\uFF00-\uFFEF]', name):
        return False

    return True

def validate_student_name(name: str):
    """
    Validate student name.
    1. If the name is in Latin characters, it should be capitalized, and separated by space.
    2. If the name is CJK name, it should be in the correct format.
    3. Should not be empty.
    """
    if not name:
        return False

    # If the name is in Latin characters, it should be capitalized, and separated by space.
    latin = re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', name)


    # If the name is CJK name, it should be in the correct format, at most 5 characters and at least 2 characters.
    cjk = re.match(r'^[\u4e00-\u9fff\uac00-\ud7a3]{2,5}$', name)

    # XOR logic
    return bool(latin) != bool(cjk)


def validate_number(number: str):
    """
    Validate number.
    1. Should be eight digits.
    2. The first four digits reflects the year of registration, which should be in the range grade 1–3, separating school year by Aug 1st.
    3. Then the two digits indicates the class ID, no more than 30.
    4. The last two digits indicates the student ID, no more than 80.
    5. Should not duplicate with existing student number.
    """
    if not re.match(r'^\d{8}$', number):
        return False

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
        return False

    if class_id < 1 or class_id > 30:
        return False

    if student_id < 1 or student_id > 80:
        return False

    return True

def validate_past_identity(identity: str):
    """
    Validate past identity.
    1. Should be either name or number.
    2. If the identity is name, it should be in the correct format.
    3. If the identity is number, it should be in the correct format.
    """

    if validate_student_name(identity):
        return True

    if validate_number(identity):
        return True

    return False
