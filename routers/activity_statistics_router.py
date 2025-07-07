from fastapi import APIRouter
from database import db
import numpy as np
from scipy.stats import mode

router = APIRouter()


@router.get("/{activity_id}/description")
async def activity_issuance_description(activity_id: str):
    """
    Get the data description of an activity by its ID.
    It consists: mean, median, mode, standard deviation, min, max, and variance.
    :param activity_id: The ID of the activity
    """
    distribution = (
        await db.zvms_new.get_collection("activity_members")
        .find({"activity": activity_id})
        .to_list(None)
    )
    if not distribution:
        return {"code": 404, "status": "not found", "data": None}
    distribution = [float(item["duration"]) for item in distribution]
    distribution = np.array(distribution, dtype=np.float64)
    mean = np.mean(distribution).item()
    median = float(np.median(distribution))
    std_dev = np.std(distribution).item()
    min_val = np.min(distribution).item()
    max_val = np.max(distribution).item()
    variance = np.var(distribution).item()
    sum_val = np.sum(distribution).item()
    twenty_fifth = np.percentile(distribution, 25).item()
    seventy_fifth = np.percentile(distribution, 75).item()
    total = len(distribution)
    return {
        "mean": mean,
        "median": median,
        "mode": mode(distribution).mode,
        "std": std_dev,
        "min": min_val,
        "max": max_val,
        "var": variance,
        "sum": sum_val,
        "25_percentile": twenty_fifth,
        "75_percentile": seventy_fifth,
        "total": total,
    }


@router.get("/{activity_id}/layers")
async def activity_issuance_layers(activity_id: str):
    """
    Get the layers of an activity by its ID.
    :param activity_id: The ID of the activity
    """
    layers = (
        await db.zvms_new.get_collection("activity_members")
        .find({"activity": activity_id})
        .to_list(None)
    )
    distribution = (
        await db.zvms_new.get_collection("activity_members")
        .find({"activity": activity_id})
        .to_list(None)
    )
    if not distribution:
        return {"code": 404, "status": "not found", "data": None}
    distribution = [item["duration"] for item in distribution]
    distribution = np.array(distribution, dtype=np.float32)

    # Then we find different values, which indicates the layers
    unique_values = np.unique(distribution)
    layers = [
        {"value": float(value), "count": int(np.sum(distribution == value))}
        for value in unique_values
    ]
    layers.sort(key=lambda x: x["count"])
    return layers[::-1]
