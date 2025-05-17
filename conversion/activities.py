from datetime import datetime
from typing import Literal
from bson import ObjectId
import pandas as pd
from typings.activity import Activity as ActivityV1, ActivityMember as ActivityMemberV1
from typings.activity_v2 import (
    Activity as ActivityV2,
    ActivityMember as ActivityMemberV2,
)

data = pd.read_excel("data/activities.xlsx")


def tagging(
    item: str,
) -> Literal[
    "prize",
    "labor",
    "club",
    "organization",
    "activity",
    "task",
    "pratice",
    "amusement",
    "import",
    "other",
]:
    mapping = {
        "体力劳动": "labor",
        "团体参与": "organization",
        "学校任务": "tasks",
        "学校活动": "occasions",
        "数据导入": "import",
        "文体活动": "activities",
        "社会实践": "practice",
        "社团活动": "club",
        "竞赛获奖": "prize",
    }
    filtered = data[data["_id"] == f"ObjectId({item})"]["category"]
    if not filtered.empty:
        category = filtered.iloc[0]
        if category in mapping:
            return mapping[category]
        return "other"
    return "other"


def convert_activity(
    id: str, activity: ActivityV1
) -> tuple[ActivityV2, list[ActivityMemberV2]]:
    modes = [member.mode for member in activity.members]
    activity_type = (
        modes[0].value if all(mode == modes[0] for mode in modes) else "hybrid"
    )
    members = []
    for member in activity.members:
        members.append(
            ActivityMemberV2(
                member=member.id,
                activity=str(id),
                status=str(member.status.value),
                mode=str(member.mode.value),
                duration=member.duration,
                _id=str(ObjectId()),
            )
        )
    new_activity = ActivityV2(
        _id=id,
        type=str(activity_type),
        name=activity.name,
        description=activity.description,
        date=datetime.fromisoformat(activity.date),
        createdAt=datetime.fromisoformat(activity.createdAt),
        updatedAt=datetime.fromtimestamp(float(activity.updatedAt))
        if type(activity.updatedAt) == float
        else datetime.fromisoformat(activity.updatedAt),
        appointee=activity.creator,
        approver=activity.approver,
        creator=activity.creator,
        status=str(activity.status.value),
        place=activity.registration.place if activity.registration else "",
        origin=tagging(id),
    )
    return new_activity, members
