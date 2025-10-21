from bson import ObjectId
from database import db
from typings.group_v2 import Category, Group as GroupV2
from typings.group import Group as GroupV1
from typings.user import UserPosition as UserPositionV1
from typings.user_v2 import UserPosition as UserPositionV2

categories = [
    ["2025", "2026", "2027"],
    ["创新班", "文创班", "镇海班", "蛟川班", "甬江班", "帮扶班"],
    [
        "学术类社团",
        "实践类社团",
        "体艺类社团",
        "慈善类社团",
        "学生会组织",
        "其他学生组织",
    ],
]
categories_indices = ["grade", "class", "organization"]


def generate_categories():
    categories_summary = []
    for index, summary in zip(categories_indices, categories):
        for category in summary:
            model = Category(
                _id=str(ObjectId()), type=index, name=category, description=""
            ).model_dump()
            categories_summary.append(model)

    cates = db.zvms_new.get_collection("categories")
    cates.insert_many(categories_summary)


def get_class_type(class_name: str):
    if class_name.startswith("高") and ("9" in class_name or "10" in class_name):
        return "帮扶班"
    elif class_name.startswith("高") and "2" in class_name and "一" not in class_name:
        return "文创班"
    elif class_name.startswith("高") and ("1" in class_name or "2" in class_name):
        return "创新班"
    elif class_name.startswith("高") and "8" in class_name and "三" not in class_name:
        return "甬江班"
    elif class_name.startswith("高"):
        return "镇海班"
    elif class_name.startswith("蛟") and ("1" in class_name or "2" in class_name):
        return "创新班"
    else:
        return "蛟川班"


def get_grade_type(grade_name: str):
    if "三" in grade_name:
        return "2025"
    elif "二" in grade_name:
        return "2026"
    elif "一" in grade_name:
        return "2027"
    raise ValueError(f"Unknown grade name: {grade_name}")


async def trans_group(id: str, group: GroupV1) -> GroupV2:
    new_type = "class" if group.type.value == "class" else "organization"
    charge = await db.zvms.get_collection("users").find_one({"group": id})
    charge = charge["_id"] if group.type.value == "class" else ""
    categs = []
    if new_type == "class":
        class_type = get_class_type(group.name)
        grade_type = get_grade_type(group.name)

        class_cate_id = await db.zvms_new.get_collection("categories").find_one(
            {"name": class_type, "type": "class"}
        )
        grade_cate_id = await db.zvms_new.get_collection("categories").find_one(
            {"name": grade_type, "type": "grade"}
        )

        categs.append(str(class_cate_id["_id"]))
        categs.append(str(grade_cate_id["_id"]))

    return GroupV2(
        _id=id,
        name=group.name,
        type=new_type,
        description=group.description or "",
        charge=str(charge),
        contact=str(charge),  # TODO: contact is not implemented yet
        permissions=[trans_permissions(perm) for perm in group.permissions],
        categories=categs,
    )


def trans_permissions(permission: UserPositionV1) -> UserPositionV2:
    mapping = {
        UserPositionV1.student: "student",
        UserPositionV1.secretary: "monitor",
        UserPositionV1.department: "volunteer",
        UserPositionV1.admin: "admin",
        "volunteer": "volunteer",
        "monitor": "monitor",
        "admin": "admin",
        "student": "student",
        "club": "club",
    }
    return mapping.get(permission, "student")
