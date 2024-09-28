# import pandas as pd
# from h11 import Request
# from pydantic import BaseModel
#
# from typings.export import Export, ExportFormat, ExportStatus, ExportResponse
# from fastapi import APIRouter, Depends, HTTPException, Response
# from bson import ObjectId
# from database import connect_to_mongo, db
# from util.time_export import calculate, json2csv, json2xlsx
# from utils import get_current_user
# from uuid import uuid4
# import datetime
# import asyncio
#
# router = APIRouter()
#
# exports: list[ExportResponse] = []
#
#
# @router.post('')
# async def create_exports(
#     # mode: Export,
#     # user=Depends(get_current_user)
# ):
#     pipeline = \
#         [
#             {
#                 '$lookup': {
#                     'from': 'activities',
#                     'let': {
#                         'userIdStr': {
#                             '$toString': '$_id'
#                         }
#                     },
#                     'pipeline': [
#                         {
#                             '$unwind': '$members'
#                         }, {
#                             '$match': {
#                                 '$expr': {
#                                     '$and': [
#                                         {
#                                             '$eq': [
#                                                 '$members._id', '$$userIdStr'
#                                             ]
#                                         }, {
#                                             '$eq': [
#                                                 '$members.status', 'effective'
#                                             ]
#                                         }
#                                     ]
#                                 }
#                             }
#                         }
#                     ],
#                     'as': 'user_activities'
#                 }
#             }, {
#                 '$addFields': {
#                     'groupObjectIds': {
#                         '$map': {
#                             'input': '$group',
#                             'as': 'groupIdStr',
#                             'in': {
#                                 '$toObjectId': '$$groupIdStr'
#                             }
#                         }
#                     }
#                 }
#             }, {
#                 '$lookup': {
#                     'from': 'groups',
#                     'let': {
#                         'userGroups': '$groupObjectIds'
#                     },
#                     'pipeline': [
#                         {
#                             '$match': {
#                                 '$expr': {
#                                     '$and': [
#                                         {
#                                             '$in': [
#                                                 '$_id', '$$userGroups'
#                                             ]
#                                         }, {
#                                             '$eq': [
#                                                 '$type', 'class'
#                                             ]
#                                         }
#                                     ]
#                                 }
#                             }
#                         }, {
#                             '$project': {
#                                 'name': 1
#                             }
#                         }
#                     ],
#                     'as': 'user_classes'
#                 }
#             }, {
#                 '$unwind': '$user_activities'
#             }, {
#                 '$group': {
#                     '_id': {
#                         'userId': '$_id',
#                         'mode': '$user_activities.members.mode',
#                         'name': '$name',
#                         'userIdNumber': '$id',
#                         'class': {
#                             '$arrayElemAt': [
#                                 '$user_classes.name', 0
#                             ]
#                         }
#                     },
#                     'totalDuration': {
#                         '$sum': '$user_activities.members.duration'
#                     }
#                 }
#             }, {
#                 '$group': {
#                     '_id': '$_id.userId',
#                     'name': {
#                         '$first': '$_id.name'
#                     },
#                     'id': {
#                         '$first': '$_id.userIdNumber'
#                     },
#                     'class': {
#                         '$first': '$_id.class'
#                     },
#                     'modes': {
#                         '$push': {
#                             'mode': '$_id.mode',
#                             'totalDuration': '$totalDuration'
#                         }
#                     }
#                 }
#             }, {
#                 '$project': {
#                     '_id': 0,
#                     'id': 1,
#                     'name': 1,
#                     'class': 1,
#                     'on_campus': {
#                         '$cond': {
#                             'if': {
#                                 '$in': [
#                                     'on-campus', '$modes.mode'
#                                 ]
#                             },
#                             'then': {
#                                 '$arrayElemAt': [
#                                     {
#                                         '$filter': {
#                                             'input': '$modes',
#                                             'as': 'mode',
#                                             'cond': {
#                                                 '$eq': [
#                                                     '$$mode.mode', 'on-campus'
#                                                 ]
#                                             }
#                                         }
#                                     }, 0
#                                 ]
#                             },
#                             'else': {
#                                 'mode': 'on-campus',
#                                 'totalDuration': 0
#                             }
#                         }
#                     },
#                     'off_campus': {
#                         '$cond': {
#                             'if': {
#                                 '$in': [
#                                     'off-campus', '$modes.mode'
#                                 ]
#                             },
#                             'then': {
#                                 '$arrayElemAt': [
#                                     {
#                                         '$filter': {
#                                             'input': '$modes',
#                                             'as': 'mode',
#                                             'cond': {
#                                                 '$eq': [
#                                                     '$$mode.mode', 'off-campus'
#                                                 ]
#                                             }
#                                         }
#                                     }, 0
#                                 ]
#                             },
#                             'else': {
#                                 'mode': 'off-campus',
#                                 'totalDuration': 0
#                             }
#                         }
#                     },
#                     'social_practice': {
#                         '$cond': {
#                             'if': {
#                                 '$in': [
#                                     'social-practice', '$modes.mode'
#                                 ]
#                             },
#                             'then': {
#                                 '$arrayElemAt': [
#                                     {
#                                         '$filter': {
#                                             'input': '$modes',
#                                             'as': 'mode',
#                                             'cond': {
#                                                 '$eq': [
#                                                     '$$mode.mode', 'social-practice'
#                                                 ]
#                                             }
#                                         }
#                                     }, 0
#                                 ]
#                             },
#                             'else': {
#                                 'mode': 'social-practice',
#                                 'totalDuration': 0
#                             }
#                         }
#                     }
#                 }
#             }, {
#                 '$project': {
#                     'id': 1,
#                     'name': 1,
#                     'class': 1,
#                     'on-campus': '$on_campus.totalDuration',
#                     'off-campus': '$off_campus.totalDuration',
#                     'social-practice': '$social_practice.totalDuration'
#                 }
#             }
#         ]
#     result = await db.zvms.activities.aggregate(pipeline).to_list(None)
#     df = pd.DataFrame(result)
#     print(df)
#     return 123
