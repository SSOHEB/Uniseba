"""Typed queue message models with backward-compatible dict conversion."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OCRRefreshing:
    """Signal that OCR is refreshing due to a major visible change."""

    changed_regions: int
    total_regions: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "refreshing",
            "changed_regions": int(self.changed_regions),
            "total_regions": int(self.total_regions),
        }

    @staticmethod
    def from_obj(obj: Any) -> Optional["OCRRefreshing"]:
        if isinstance(obj, OCRRefreshing):
            return obj
        if isinstance(obj, dict) and obj.get("type") == "refreshing":
            return OCRRefreshing(
                changed_regions=int(obj.get("changed_regions", 0)),
                total_regions=int(obj.get("total_regions", 0)),
            )
        return None


@dataclass
class OCRIndexUpdate:
    """Signal carrying a full OCR index snapshot."""

    index: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "index", "index": self.index}

    @staticmethod
    def from_obj(obj: Any) -> Optional["OCRIndexUpdate"]:
        if isinstance(obj, OCRIndexUpdate):
            return obj
        if isinstance(obj, dict) and obj.get("type") == "index":
            index = obj.get("index", [])
            if isinstance(index, list):
                return OCRIndexUpdate(index=index)
        if isinstance(obj, list):
            # Backward compatibility for older producers that pushed raw index lists.
            return OCRIndexUpdate(index=obj)
        return None


def parse_ocr_message(obj: Any) -> Optional[Any]:
    """Parse a queue payload into OCRRefreshing/OCRIndexUpdate when possible."""
    refreshing = OCRRefreshing.from_obj(obj)
    if refreshing is not None:
        return refreshing
    return OCRIndexUpdate.from_obj(obj)


@dataclass
class SemanticRequest:
    """Request payload sent from UI thread to semantic worker."""

    token: int
    query: str
    index: List[Dict[str, Any]]
    limit: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": int(self.token),
            "query": str(self.query),
            "index": self.index,
            "limit": int(self.limit),
        }

    @staticmethod
    def from_obj(obj: Any) -> Optional["SemanticRequest"]:
        if isinstance(obj, SemanticRequest):
            return obj
        if isinstance(obj, dict):
            if "token" in obj and "query" in obj and "index" in obj and "limit" in obj:
                index = obj.get("index", [])
                if isinstance(index, list):
                    return SemanticRequest(
                        token=int(obj["token"]),
                        query=str(obj["query"]),
                        index=index,
                        limit=int(obj["limit"]),
                    )
        return None


@dataclass
class SemanticResult:
    """Result payload sent from semantic worker back to UI thread."""

    token: int
    results: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {"token": int(self.token), "results": self.results}

    @staticmethod
    def from_obj(obj: Any) -> Optional["SemanticResult"]:
        if isinstance(obj, SemanticResult):
            return obj
        if isinstance(obj, dict) and "token" in obj and "results" in obj:
            results = obj.get("results", [])
            if isinstance(results, list):
                return SemanticResult(token=int(obj["token"]), results=results)
        return None

