from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any
from database import db
from util.object_id import get_current_user, validate_object_id
import re

router = APIRouter()

# MCP (Model Context Protocol) Server Endpoints
# These endpoints provide read-only access to activity data for AI agents and tools
# No sensitive operations or authentication bypasses are included


@router.get("/activities")
async def mcp_get_activities(
    page: int = Query(1, ge=1, description="Page number"),
    perpage: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str = Query("", description="Search term for activity names"),
    activity_type: str = Query("all", description="Filter by activity type"),
    sort: str = Query("_id", description="Sort field"),
    asc: bool = Query(False, description="Sort in ascending order"),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    MCP endpoint to retrieve activities with pagination and filtering.
    Read-only access to activity data for AI agents.
    """

    # Validate activity types
    if activity_type == "all" or activity_type == "":
        target_types = ["on-campus", "off-campus", "social-practice", "hybrid"]
    else:
        target_types = activity_type.split(",")
        valid_types = ["on-campus", "off-campus", "social-practice", "hybrid"]
        target_types = [t for t in target_types if t in valid_types]
        if not target_types:
            target_types = valid_types

    # Escape search term for safety
    search = re.escape(search) if search else ""

    document_filter = {
        "$and": [
            {"name": {"$regex": search, "$options": "i"}},
            {"type": {"$in": target_types}},
        ]
    }

    # Get total count
    count = await db.zvms_new.get_collection("activities").count_documents(
        document_filter
    )

    # Build aggregation pipeline
    pipeline = [
        {"$match": document_filter},
        {"$sort": {sort: 1 if asc else -1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "name": 1,
                "description": 1,
                "type": 1,
                "date": 1,
                "location": 1,
                "duration": 1,
                "status": 1,
                "creator": 1,
                "createdAt": 1,
                "updatedAt": 1,
            }
        },
    ]

    activities = (
        await db.zvms_new.get_collection("activities").aggregate(pipeline).to_list(None)
    )

    return {
        "success": True,
        "data": {
            "activities": activities,
            "pagination": {
                "total": count,
                "page": page,
                "perpage": perpage,
                "totalPages": (count + perpage - 1) // perpage,
            },
        },
    }


@router.get("/activities/{activity_id}")
async def mcp_get_activity_details(
    activity_id: str, user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    MCP endpoint to retrieve detailed information about a specific activity.
    Read-only access for AI agents.
    """

    try:
        activity_oid = validate_object_id(activity_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid activity ID format")

    activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": activity_oid},
        {
            "_id": 0,
            "name": 1,
            "description": 1,
            "type": 1,
            "date": 1,
            "location": 1,
            "duration": 1,
            "status": 1,
            "creator": 1,
            "createdAt": 1,
            "updatedAt": 1,
        },
    )

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get member count
    members_count = await db.zvms_new.get_collection(
        "activity_members"
    ).count_documents({"activity": activity_id})

    activity["id"] = activity_id
    activity["members_count"] = members_count

    return {"success": True, "data": activity}


@router.get("/activities/{activity_id}/statistics")
async def mcp_get_activity_statistics(
    activity_id: str, user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    MCP endpoint to retrieve statistical data for an activity.
    Provides aggregated statistics without exposing individual member data.
    """

    try:
        validate_object_id(activity_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid activity ID format")

    # Check if activity exists
    activity_exists = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}, {"_id": 1}
    )

    if not activity_exists:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get activity member durations for statistics
    members = (
        await db.zvms_new.get_collection("activity_members")
        .find({"activity": activity_id}, {"duration": 1, "_id": 0})
        .to_list(None)
    )

    if not members:
        return {"success": True, "data": {"total_members": 0, "statistics": None}}

    import numpy as np
    from scipy.stats import mode

    durations = [float(member["duration"]) for member in members]
    durations_array = np.array(durations, dtype=np.float64)

    statistics = {
        "total_members": len(durations),
        "mean_duration": float(np.mean(durations_array)),
        "median_duration": float(np.median(durations_array)),
        "std_deviation": float(np.std(durations_array)),
        "min_duration": float(np.min(durations_array)),
        "max_duration": float(np.max(durations_array)),
        "total_duration": float(np.sum(durations_array)),
        "variance": float(np.var(durations_array)),
        "percentile_25": float(np.percentile(durations_array, 25)),
        "percentile_75": float(np.percentile(durations_array, 75)),
    }

    return {"success": True, "data": statistics}


@router.get("/activities/types/summary")
async def mcp_get_activity_types_summary(
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    MCP endpoint to get a summary of activities by type.
    Provides aggregate counts without sensitive details.
    """

    pipeline = [
        {
            "$group": {
                "_id": "$type",
                "count": {"$sum": 1},
                "statuses": {"$push": "$status"},
            }
        },
        {
            "$project": {
                "type": "$_id",
                "total_count": "$count",
                "status_breakdown": {
                    "$reduce": {
                        "input": "$statuses",
                        "initialValue": {},
                        "in": {
                            "$mergeObjects": [
                                "$$value",
                                {
                                    "$arrayToObject": [
                                        [
                                            {
                                                "k": "$$this",
                                                "v": {
                                                    "$add": [
                                                        {
                                                            "$ifNull": [
                                                                {
                                                                    "$getField": {
                                                                        "field": "$$this",
                                                                        "input": "$$value",
                                                                    }
                                                                },
                                                                0,
                                                            ]
                                                        },
                                                        1,
                                                    ]
                                                },
                                            }
                                        ]
                                    ]
                                },
                            ]
                        },
                    }
                },
            }
        },
    ]

    results = (
        await db.zvms_new.get_collection("activities").aggregate(pipeline).to_list(None)
    )

    summary = {}
    total_activities = 0

    for result in results:
        activity_type = result["type"]
        count = result["total_count"]
        total_activities += count

        summary[activity_type] = {
            "count": count,
            "status_breakdown": result.get("status_breakdown", {}),
        }

    return {
        "success": True,
        "data": {"total_activities": total_activities, "by_type": summary},
    }


@router.get("/activities/search/suggestions")
async def mcp_get_activity_search_suggestions(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum suggestions"),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    MCP endpoint to get activity name suggestions for search functionality.
    Helps AI agents provide better search assistance.
    """

    # Escape the query for regex safety
    escaped_query = re.escape(query)

    pipeline = [
        {"$match": {"name": {"$regex": escaped_query, "$options": "i"}}},
        {"$project": {"_id": {"$toString": "$_id"}, "name": 1, "type": 1}},
        {"$limit": limit},
    ]

    suggestions = (
        await db.zvms_new.get_collection("activities").aggregate(pipeline).to_list(None)
    )

    return {"success": True, "data": {"query": query, "suggestions": suggestions}}
