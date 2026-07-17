from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from secure_knowledge_core.core.logging import request_id_context
from secure_knowledge_core.core.tracing import set_span_attributes, start_span


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = (
            request.headers.get("X-Request-ID")
            or str(uuid4())
        )

        token = request_id_context.set(request_id)

        try:
            with start_span(
                "http.request",
                {
                    "request_id": request_id,
                    "http.method": request.method,
                },
            ) as span:
                response = await call_next(request)
                set_span_attributes(
                    span,
                    {
                        "http.status_code": response.status_code,
                        "status": (
                            "succeeded"
                            if response.status_code < 500
                            else "failed"
                        ),
                    },
                )
                response.headers["X-Request-ID"] = request_id
                return response
        finally:
            request_id_context.reset(token)
