# Phase 9 Task 6: api_client.py decomposition
# Domain classes composed into ApiClient facade.
from src.api.labels import LabelResolver
from src.api.async_jobs import AsyncJobManager
from src.api.traffic_query import TrafficQueryBuilder

__all__ = ["LabelResolver", "AsyncJobManager", "TrafficQueryBuilder"]
