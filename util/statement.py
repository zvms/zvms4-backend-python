from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from config import BASE_ON_CAMPUS, BASE_OFF_CAMPUS, BASE_SOCIAL_PRACTICE
from database import db, connect_to_mongo
from bson import ObjectId
from settings import CHINESE_FONT
from typings.time import UserTimeStat, UserActivityTime
from typings.user_v2 import UserActivityTimeSums
from util.calculate import calculate_user_time, generate_description
from util.get_class import get_user_class, get_user_classname
from utils import validate_object_id

# Language type definition
Language = Literal["zh", "en"]

# Translation dictionaries
TRANSLATIONS = {
    "zh": {
        "volunteer_statement": "义工明细",
        "signature": "镇海中学义工管理平台 | 学生会实践部",
        "name": "姓名",
        "student_id": "学号",
        "class": "班级",
        "database_id": "数据库 ID",
        "export_time": "导出时间",
        "export_period": "导出周期",
        "volunteer_statistics": "义工时长统计",
        "volunteer_statistics_this_year": "本学年义工时长统计",
        "category": "统计项目",
        "total_hours": "总时长",
        "on_campus": "校内",
        "off_campus": "校外",
        "social_practice": "社会实践",
        "effective_hours": "有效时长",
        "volunteer_hours": "义工时长",
        "required_hours": "要求最低时长",
        "reached_target": "已达标",
        "not_reached_target": "未达标",
        "target_status": "达标状态",
        "target": "根据平台数据，该同学义工时长已达到要求",
        "volunteer_hours_this_year": "本学年义工时长",
        "hours": "小时",
        "volunteer_service_records": "义工记录明细",
        "activity_name": "义工名称",
        "date": "日期",
        "recording_mode": "记入模式",
        "duration": "计入时长",
        "person_in_charge": "负责人",
        "sgn": "镇海中学团委 学生会实践部",
        "stmt": "本明细由平台数据导出自动生成，经团委审核、盖章后生效。未经审核的明细不具备证明效力。",
        "spreadsheet": {
            "_id": "数据库 ID",
            "name": "姓名",
            "id": "学号",
            "group": "班级",
            "on-campus": "校内",
            "off-campus": "校外",
            "social-practice": "社会实践",
            "ay-on-campus": "本学年校内",
            "ay-off-campus": "本学年校外",
            "ay-social-practice": "本学年社会实践",
            "description": "明细",
            "filename": "义工明细表",
        },
    },
    "en": {
        "volunteer_statement": "Volunteer Details",
        "signature": "Zhenhai High School Volunteer Management System | Department of Practice, Student Union",
        "name": "Name",
        "student_id": "Student ID",
        "class": "Class",
        "database_id": "Database ID",
        "export_time": "Export Time",
        "export_period": "Export Period",
        "volunteer_statistics": "Volunteer Statistics",
        "volunteer_statistics_this_year": "Volunteer Statistics this Year",
        "category": "Category",
        "total_hours": "Total Hours",
        "on_campus": "On-Campus",
        "off_campus": "Off-Campus",
        "social_practice": "Social Practice",
        "effective_hours": "Effective Hours",
        "volunteer_hours": "Volunteer Hours",
        "required_hours": "Required Minimum Hours",
        "reached_target": "Target Reached",
        "not_reached_target": "Target Not Reached",
        "target_status": "Target Status",
        "volunteer_hours_this_year": "Volunteer Hours this Year",
        "hours": "Hours",
        "volunteer_service_records": "Volunteer Service Records",
        "activity_name": "Activity Name",
        "date": "Date",
        "recording_mode": "Recording Mode",
        "duration": "Duration",
        "person_in_charge": "Person in Charge",
        "sgn": "Zhenhai High School Youth League Committee & Student Union Department of Practice",
        "stmt": "This statement is automatically generated from platform data and is valid after review and stamping by the Youth League Committee. Unreviewed statements do not have proof of validity.",
        "spreadsheet": {
            "_id": "Database ID",
            "name": "Name",
            "id": "Student ID",
            "group": "Class",
            "on-campus": "On-Campus",
            "off-campus": "Off-Campus",
            "social-practice": "Social Practice",
            "ay-on-campus": "On-Campus this Year",
            "ay-off-campus": "Off-Campus this Year",
            "ay-social-practice": "Social Practice this Year",
            "description": "Details",
            "filename": "Volunteer Details Sheet",
        },
    },
    "jp": {
        "volunteer_statement": "ボランティア明細",
        "signature": "鎮海中学校ボランティア管理システム | 学生会実践部",
        "name": "名前",
        "student_id": "学生ID",
        "class": "クラス",
        "database_id": "データベースID",
        "export_time": "エクスポート時間",
        "export_period": "エクスポート期間",
        "volunteer_statistics": "ボランティア時間統計",
        "volunteer_statistics_this_year": "今年のボランティア時間統計",
        "category": "統計項目",
        "total_hours": "総時間",
        "on_campus": "校内",
        "off_campus": "校外",
        "social_practice": "社会実践",
        "effective_hours": "有効時間",
        "volunteer_hours": "ボランティア時間",
        "required_hours": "必要最低時間",
        "reached_target": "目標達成",
        "not_reached_target": "目標未達成",
        "target_status": "目標状態",
        "volunteer_hours_this_year": "今年のボランティア時間",
        "hours": "時間",
        "volunteer_service_records": "ボランティアサービス記録詳細",
        "activity_name": "活動名",
        "date": "日付",
        "recording_mode": "記録モード",
        "duration": "サービス時間",
        "person_in_charge": "担当者",
        "sgn": "鎮海中学校青年団委員会 学生会実践部",
        "stmt": "この明細はプラットフォームデータから自動生成され、青年団委員会の審査とスタンプ後に有効になります。未審査の明細は証明力を持ちません。",
        "spreadsheet": {
            "_id": "データベースID",
            "name": "名前",
            "id": "学生ID",
            "group": "クラス",
            "on-campus": "校内",
            "off-campus": "校外",
            "social-practice": "社会実践",
            "ay-on-campus": "今年の校内",
            "ay-off-campus": "今年の校外",
            "ay-social-practice": "今年の社会実践",
            "description": "明細",
            "filename": "ボランティア明細表",
        },
    },
}


# Pydantic models for data validation
class UserData(BaseModel):
    name: str = Field(..., description="User's full name")
    student_id: str = Field(..., description="Student ID number")
    class_name: str = Field(..., description="Class name")
    database_id: Optional[str] = Field(None, description="Database ID")
    export_time: str = Field(..., description="Export timestamp")
    export_period: Optional[str] = Field(None, description="Export period range")


class StatsData(BaseModel):
    on_campus_hours: float = Field(0, description="Total on-campus volunteer hours")
    off_campus_hours: float = Field(0, description="Total off-campus volunteer hours")
    social_practice_hours: float = Field(0, description="Total social practice hours")

    @property
    def total_hours(self) -> float:
        """Calculate total volunteer hours"""
        return self.on_campus_hours + self.off_campus_hours + self.social_practice_hours


class StatementRecord(BaseModel):
    name: str = Field(..., description="Activity name")
    date: str = Field(..., description="Activity date")
    recording_mode: str = Field(..., description="Recording mode: on, off, or social")
    duration: float = Field(..., description="Service duration in hours")
    person_in_charge_name: str = Field(..., description="Person in charge name")
    person_in_charge_id: str = Field(..., description="Person in charge ID")


class VolunteerStatementData(BaseModel):
    user_data: UserData
    stats_data: StatsData
    stats_data_raw: StatsData
    stats_data_this_year: StatsData
    statement_data: List[StatementRecord] = Field(default_factory=list)
    header_icon_path: Optional[str] = Field(None, description="Path to header icon")


class VolunteerStatementGenerator:
    def __init__(self, language: Language = "zh"):
        self.language = language
        self.translations = TRANSLATIONS[language]
        self.chinese_font = self.setup_chinese_fonts()
        self.styles = self.create_styles()

    def setup_chinese_fonts(self):
        """Register Chinese fonts for ReportLab"""
        font_paths = [
            CHINESE_FONT,
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/arphic/uming.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "./fonts/NotoSansCJK-Regular.otf",  # Local font file
        ]

        for font_path in font_paths:
            if os.path.exists(font_path) and self.language == "zh":
                try:
                    pdfmetrics.registerFont(TTFont("Chinese", font_path))
                    return "Chinese"
                except Exception as e:
                    print(f"Failed to load font {font_path}: {e}")
                    continue

        print("Warning: No Chinese font found, using Times")
        return "Times-Roman"

    def create_styles(self):
        """Create custom paragraph styles"""
        styles = getSampleStyleSheet()

        # Header title style
        styles.add(
            ParagraphStyle(
                name="HeaderTitle",
                parent=styles["Heading1"],
                fontName=self.chinese_font,
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=6 * mm,
                textColor=colors.black,
            )
        )

        # Signature style
        styles.add(
            ParagraphStyle(
                name="Signature",
                parent=styles["Normal"],
                fontName=self.chinese_font,
                fontSize=10,
                alignment=TA_RIGHT,
                textColor=colors.grey,
                spaceBefore=3 * mm,
            )
        )

        # User info style
        styles.add(
            ParagraphStyle(
                name="UserInfo",
                parent=styles["Normal"],
                fontName=self.chinese_font,
                fontSize=11,
                alignment=TA_LEFT,
                spaceAfter=2 * mm,
            )
        )

        # Small grey text style
        styles.add(
            ParagraphStyle(
                name="SmallGrey",
                parent=styles["Normal"],
                fontName=self.chinese_font,
                fontSize=9,
                textColor=colors.HexColor("#dddddd"),
                alignment=TA_LEFT,
            )
        )

        # Stats panel style
        styles.add(
            ParagraphStyle(
                name="StatsTitle",
                parent=styles["Normal"],
                fontName=self.chinese_font,
                fontSize=12,
                alignment=TA_CENTER,
                textColor=colors.black,
                spaceBefore=5 * mm,
                spaceAfter=3 * mm,
            )
        )

        # Signature text style
        styles.add(
            ParagraphStyle(
                name="SignatureText",
                parent=styles["Normal"],
                fontName=self.chinese_font,
                fontSize=12,
                alignment=TA_RIGHT,
                spaceBefore=2 * mm,
            )
        )

        # Signature text style left
        styles.add(
            ParagraphStyle(
                name="SignatureTextLeft",
                parent=styles["Normal"],
                fontName=self.chinese_font,
                fontSize=12,
                alignment=TA_LEFT,
                spaceBefore=2 * mm,
            )
        )

        return styles

    def create_header(self, user_name: str, header_icon_path: Optional[str] = None):
        """Create header with icon, title and signature"""
        elements = []

        # Header with icon (if provided)
        if header_icon_path and os.path.exists(header_icon_path):
            # Create a table with icon and title
            header_data = []
            try:
                icon = Image(header_icon_path, width=20 * mm, height=20 * mm)
                title_text = f"{user_name}{' ' if self.language == 'en' else ''}{self.translations['volunteer_statement']}"
                title = Paragraph(title_text, self.styles["HeaderTitle"])
                header_data = [[icon, title]]

                header_table = Table(header_data, colWidths=[25 * mm, 160 * mm])
                header_table.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (0, 0), "CENTER"),
                            ("ALIGN", (1, 0), (1, 0), "LEFT"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                elements.append(header_table)
            except:
                # Fallback to text-only header
                title_text = f"{user_name} {self.translations['volunteer_statement']}"
                elements.append(Paragraph(title_text, self.styles["HeaderTitle"]))
        else:
            title_text = f"{user_name} {self.translations['volunteer_statement']}"
            elements.append(Paragraph(title_text, self.styles["HeaderTitle"]))

        # Signature
        signature = Paragraph(self.translations["signature"], self.styles["Signature"])
        elements.append(signature)
        elements.append(Spacer(1, 10 * mm))

        return elements

    def create_user_info(self, user_data: UserData):
        """Create user information section"""
        elements = []

        # Database ID (small grey text)
        if user_data.database_id:
            db_id = Paragraph(
                f"{self.translations['database_id']}: {user_data.database_id}",
                self.styles["SmallGrey"],
            )
            elements.append(db_id)

        # User basic info
        user_info = [
            f"{self.translations['name']}: {user_data.name}",
            f"{self.translations['student_id']}: {user_data.student_id}",
            f"{self.translations['class']}: {user_data.class_name}",
        ]

        for info in user_info:
            elements.append(Paragraph(info, self.styles["UserInfo"]))

        # Export info
        export_info = Paragraph(
            f"{self.translations['export_time']}: {user_data.export_time}",
            self.styles["UserInfo"],
        )
        elements.append(export_info)

        if user_data.export_period:
            period_info = Paragraph(
                f"{self.translations['export_period']}: {user_data.export_period}",
                self.styles["UserInfo"],
            )
            elements.append(period_info)

        elements.append(Spacer(1, 8 * mm))
        return elements

    def create_stats_panel(
        self, raw: StatsData, overall: StatsData, this_year: StatsData
    ):
        """Create statistics panel showing only total hours for each category"""
        elements = []

        # Stats title
        title_key = "volunteer_statistics"
        stats_title = Paragraph(self.translations[title_key], self.styles["StatsTitle"])
        elements.append(stats_title)

        get_target_status = (
            lambda a, b: self.translations["reached_target"]
            if a >= b
            else self.translations["not_reached_target"]
        )

        # Create stats table - only showing hours, not counts
        stats_table_data = [
            [
                self.translations["category"],
                self.translations["on_campus"],
                self.translations["off_campus"],
                self.translations["social_practice"],
                self.translations["total_hours"],
            ],
            [
                self.translations["effective_hours"],
                f"{overall.on_campus_hours} {self.translations['hours']}",
                f"{overall.off_campus_hours} {self.translations['hours']}",
                f"{overall.social_practice_hours} {self.translations['hours']}",
                f"{overall.total_hours} {self.translations['hours']}",
            ],
            [
                self.translations["volunteer_hours"],
                f"{raw.on_campus_hours} {self.translations['hours']}",
                f"{raw.off_campus_hours} {self.translations['hours']}",
                f"{raw.social_practice_hours} {self.translations['hours']}",
                f"{raw.total_hours} {self.translations['hours']}",
            ],
            [
                self.translations["required_hours"],
                f"{BASE_ON_CAMPUS} {self.translations['hours']}",
                f"{BASE_OFF_CAMPUS} {self.translations['hours']}",
                f"{BASE_SOCIAL_PRACTICE} {self.translations['hours']}",
                "N/A",
            ],
            [
                self.translations["target_status"],
                get_target_status(raw.on_campus_hours, BASE_ON_CAMPUS),
                get_target_status(raw.off_campus_hours, BASE_OFF_CAMPUS),
                get_target_status(raw.social_practice_hours, BASE_SOCIAL_PRACTICE),
                f"N/A",
            ],
            [
                self.translations["volunteer_hours_this_year"],
                f"{this_year.on_campus_hours} {self.translations['hours']}",
                f"{this_year.off_campus_hours} {self.translations['hours']}",
                f"{this_year.social_practice_hours} {self.translations['hours']}",
                f"{this_year.total_hours} {self.translations['hours']}",
            ],
        ]

        stats_table = Table(
            stats_table_data, colWidths=[50 * mm, 30 * mm, 30 * mm, 30 * mm, 35 * mm]
        )
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, -1), self.chinese_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(stats_table)
        elements.append(Spacer(1, 10 * mm))
        return elements

    def create_statement_table(self, statement_data: List[StatementRecord]):
        """Create the main statement table"""
        elements = []

        # Table title
        table_title = Paragraph(
            self.translations["volunteer_service_records"], self.styles["StatsTitle"]
        )
        elements.append(table_title)

        # Table headers
        headers = [
            self.translations["activity_name"],
            self.translations["date"],
            self.translations["recording_mode"],
            self.translations["duration"],
            self.translations["person_in_charge"],
        ]

        # Create table data
        table_data = [headers]

        for record in statement_data:
            # Format recording mode
            mode_map = {
                "on": self.translations["on_campus"],
                "off": self.translations["off_campus"],
                "social": self.translations["social_practice"],
            }
            mode_text = mode_map.get(record.recording_mode, record.recording_mode)

            # Format person in charge
            person_in_charge = (
                f"{record.person_in_charge_name} ({record.person_in_charge_id})"
            )

            row = [
                record.name,
                record.date,
                mode_text,
                f"{record.duration} {self.translations['hours']}",
                person_in_charge,
            ]
            table_data.append(row)

        # Create table
        statement_table = Table(
            table_data, colWidths=[75 * mm, 25 * mm, 30 * mm, 25 * mm, 45 * mm]
        )
        statement_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Activity name left-aligned
                    ("FONTNAME", (0, 0), (-1, -1), self.chinese_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    # Alternate row colors
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ]
            )
        )

        # Add alternate row coloring
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                statement_table.setStyle(
                    TableStyle(
                        [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f9f9f9"))]
                    )
                )

        elements.append(statement_table)
        return elements

    def create_signature(self, filename: str):
        """Generate signature paragraph, on the end of the document and text aligns to the right"""
        signature_text = self.translations["sgn"]
        # date: chinese: YYYY 年 MM 月 DD 日, english: MMM DD, YYYY
        date = (
            datetime.now().strftime("%Y 年 %m 月 %d 日")
            if self.language == "zh"
            else datetime.now().strftime("%B %d, %Y")
        )
        return [
            Paragraph(self.translations["stmt"], self.styles["SignatureTextLeft"]),
            Paragraph(date, self.styles["SignatureText"]),
            Paragraph(signature_text, self.styles["SignatureText"]),
        ]

    def generate_statement(self, filename: str, data: VolunteerStatementData):
        """Generate complete volunteer statement PDF"""
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        elements = []

        # Add all sections
        elements.extend(self.create_header(data.user_data.name, data.header_icon_path))
        elements.extend(self.create_user_info(data.user_data))
        elements.extend(
            self.create_stats_panel(
                raw=data.stats_data_raw,
                overall=data.stats_data,
                this_year=data.stats_data_this_year,
            )
        )
        elements.extend(self.create_statement_table(data.statement_data))
        elements.extend(self.create_signature(filename))

        # Build PDF
        doc.build(elements)
        print(f"Volunteer statement generated: {filename}")


# Function to create statement from your kernel data
async def create_statement_from_kernel_data(
    id: str,
    period: tuple[datetime, datetime],
    filename: str = "volunteer_statement.pdf",
    language: Language = "zh",
):
    """
    Create volunteer statement from your kernel data

    Args:
        id: Unique identifier for the user (e.g., student ID)
        period: Tuple containing start and end dates for the statement period
        filename: Name of the output PDF file
        language: Language for the statement ("zh" for Chinese, "en" for English)
    """

    user = await db.zvms.get_collection("users").find_one(
        {"_id": validate_object_id(id)}
    )
    user_name = user.get("name", "Unknown User")
    student_id = user.get("id", "Unknown ID")
    class_id = await get_user_classname(id)

    # Create Pydantic models from kernel data
    user_data = UserData(
        name=user_name,
        student_id=student_id,
        class_name=class_id,
        database_id=str(user["_id"]),
        export_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        export_period=f"{period[0].strftime('%Y年%m月%d日')}——{period[1].strftime('%Y年%m月%d日')}"
        if language == "zh"
        else f"{period[0].strftime('%B %d, %Y')} – {period[1].strftime('%B %d, %Y')}",
    )

    stat = await calculate_user_time(id, allow_cache=False)
    on_campus_hours = stat.get("on-campus", 0.0)
    off_campus_hours = stat.get("off-campus", 0.0)
    social_practice_hours = stat.get("social-practice", 0.0)
    stat_obj = UserActivityTime(
        _id=id,
        user=user["id"],
        on_campus_raw=on_campus_hours,
        off_campus_raw=off_campus_hours,
        social_practice=social_practice_hours,
        updated_at=datetime.now(),
    )

    stats_data = StatsData(
        on_campus_hours=round(stat_obj.on_campus, 1),
        off_campus_hours=round(stat_obj.off_campus, 1),
        social_practice_hours=stat_obj.social_practice,
    )

    raw_data = StatsData(
        on_campus_hours=stat_obj.on_campus_raw,
        off_campus_hours=stat_obj.off_campus_raw,
        social_practice_hours=stat_obj.social_practice,
    )

    now = datetime.now()
    ay = now.year if now.month >= 9 else now.year - 1
    soy = datetime.now().replace(
        month=8, day=1, year=ay, hour=0, minute=0, second=0, microsecond=0
    )
    eoy = datetime.now().replace(
        month=7, day=31, year=ay + 1, hour=23, minute=59, second=59, microsecond=999999
    )
    stat_this_year = await calculate_user_time(
        id, date_start=soy, date_end=eoy, allow_cache=False
    )
    stats_data_this_year = StatsData(
        on_campus_hours=stat_this_year.get("on-campus", 0.0),
        off_campus_hours=stat_this_year.get("off-campus", 0.0),
        social_practice_hours=stat_this_year.get("social-practice", 0.0),
    )

    statement_records = []

    items = (
        await db.zvms_new.get_collection("activity_members")
        .find({"member": id})
        .to_list(None)
    )
    type_map = {"on-campus": "on", "off-campus": "off", "social-practice": "social"}
    for item in items:
        activity = await db.zvms_new.get_collection("activities").find_one(
            {"_id": validate_object_id(item["activity"])}
        )
        assignee = activity.get("approver", "Unknown")
        if ObjectId.is_valid(assignee):
            assignee_data = await db.zvms.get_collection("users").find_one(
                {"_id": ObjectId(assignee)}
            )
        else:
            assignee_data = {
                "name": "学校团委" if language == "zh" else "Authority",
                "id": "AUTHORITY",  # Default authority ID
            }
        statement_records.append(
            StatementRecord(
                name=activity["name"],
                date=activity["date"].strftime("%Y-%m-%d"),
                recording_mode=type_map[item["mode"]],
                duration=item["duration"],
                person_in_charge_name=assignee_data.get("name", "Unknown")
                if assignee_data
                else "学校团委"
                if language == "zh"
                else "Authority",
                person_in_charge_id=assignee_data.get(
                    "id", "AUTHORITY" if language == "zh" else "Authority"
                )
                if assignee_data
                else "AUTHORITY"
                if language == "zh"
                else "Authority",
            )
        )

    # Create complete data structure
    volunteer_data = VolunteerStatementData(
        user_data=user_data,
        stats_data=stats_data,
        stats_data_raw=raw_data,
        stats_data_this_year=stats_data_this_year,
        statement_data=statement_records,
        header_icon_path="./data/pwa-192x192.png",  # Optional, can be None
    )

    # Generate PDF with specified language
    generator = VolunteerStatementGenerator(language=language)
    generator.generate_statement(filename, volunteer_data)

    description = await generate_description(id)

    spreadsheet_data = {
        "_id": user_data.database_id,
        "name": user_data.name,
        "id": user_data.student_id,
        "group": user_data.class_name,
        "on-campus": stats_data.on_campus_hours,
        "off-campus": stats_data.off_campus_hours,
        "social-practice": stats_data.social_practice_hours,
        "ay-on-campus": stats_data_this_year.on_campus_hours,
        "ay-off-campus": stats_data_this_year.off_campus_hours,
        "ay-social-practice": stats_data_this_year.social_practice_hours,
        "description": description,
    }

    return filename, spreadsheet_data


if __name__ == "__main__":

    async def main():
        await connect_to_mongo()
        # Generate both Chinese and English versions
        id = "65e6fa210edc81d012ec46d9"
        period = (datetime(2020, 1, 1), datetime(2026, 6, 30))
        await create_statement_from_kernel_data(
            id, period, filename=f"volunteer_statement_{id}.pdf", language="zh"
        )

    import asyncio

    asyncio.run(main())
