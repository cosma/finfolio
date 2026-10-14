"""FastAPI application: read-only REST API over stored digests and per-video reports.

Run locally with:
    uvicorn finfolio.api.app:app --host 127.0.0.1 --port 8000
Swagger UI is served at /docs.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from finfolio import storage
from finfolio.api import index
from finfolio.api.schemas import (
    DigestDetail,
    DigestList,
    RefreshResult,
    ReportDetail,
    ReportPage,
)

VIDEO_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

VerdictName = Literal["True", "Partially supported", "Unverified", "False"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the index from storage before serving any request (spec Edge Cases)."""
    index.build_index()
    yield


app = FastAPI(
    title="FinFolio API",
    version="0.1.0",
    description=(
        "Read-only API over stored monthly digests and per-video fact-check reports. "
        "Local, single-user service; no authentication in v1."
    ),
    lifespan=lifespan,
)


@app.exception_handler(storage.StoredFileError)
def unreadable_stored_file(request: Request, exc: storage.StoredFileError) -> JSONResponse:
    """An unparseable stored file is a data problem on the server: 500, with a message naming the file."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/digests", response_model=DigestList, tags=["digests"])
def list_digests() -> dict[str, Any]:
    """List all monthly digests, newest month first."""
    with closing(index.open_index()) as conn:
        return {"items": index.list_digests(conn)}


@app.get("/digests/{year}/{month}", response_model=DigestDetail, tags=["digests"])
def get_digest(
    year: Annotated[int, Path(ge=1000, le=9999, description="4-digit year")],
    month: Annotated[int, Path(ge=1, le=12, description="Month number, 1-12")],
) -> dict[str, Any]:
    """Return one full monthly digest, including per-channel breakdown and monetization disclosures."""
    digest = storage.load_monthly_digest(year, month)
    if digest is None:
        raise HTTPException(404, detail=f"No digest for {year:04d}-{month:02d}")
    return digest


@app.get("/reports", response_model=ReportPage, tags=["reports"])
def list_reports(
    channel: Annotated[
        str | None, Query(min_length=1, description="Exact channel name or channel URL")
    ] = None,
    start: Annotated[date | None, Query(description="Inclusive start, YYYY-MM-DD (UTC)")] = None,
    end: Annotated[date | None, Query(description="Inclusive end, YYYY-MM-DD (UTC)")] = None,
    verdict: Annotated[
        VerdictName | None,
        Query(description="Only reports with at least one claim with this verdict"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> dict[str, Any]:
    """List per-video reports, newest fact-check first. Filters combine with AND."""
    if start is not None and end is not None and start > end:
        raise HTTPException(
            422, detail=f'"start" ({start.isoformat()}) is after "end" ({end.isoformat()})'
        )
    with closing(index.open_index()) as conn:
        items, total = index.query_reports(
            conn,
            channel=channel,
            start=start,
            end=end,
            verdict=verdict,
            page=page,
            page_size=page_size,
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/reports/{video_id}", response_model=ReportDetail, tags=["reports"])
def get_report(
    video_id: Annotated[
        str,
        Path(pattern=VIDEO_ID_PATTERN, description="YouTube video ID (letters, digits, - and _)"),
    ],
) -> dict[str, Any]:
    """Return one full per-video report, as stored."""
    report = storage.load_report(video_id)
    if report is None:
        raise HTTPException(404, detail=f"No report for video ID {video_id}")
    return report


@app.post("/index/refresh", response_model=RefreshResult, tags=["index"])
def refresh_index() -> dict[str, Any]:
    """Rebuild the index from storage and swap it in. Requests keep using the old index until the swap."""
    result = index.build_index()
    return {
        "indexed": {"reports": result.reports, "digests": result.digests},
        "skipped": result.skipped,
    }
