import asyncio
from uuid import UUID

from alphaedge.config import settings
from alphaedge.modules.insights.domain.entities import InsightReport
from alphaedge.modules.insights.domain.enums import InsightStatus
from alphaedge.modules.insights.domain.prompts import PROMPT_VERSION, get_prompt, render_prompt
from alphaedge.modules.insights.infrastructure.context_loader import build_context
from alphaedge.modules.insights.infrastructure.mock_llm import MockLLMProvider
from alphaedge.modules.insights.infrastructure.models import (
    SQLAlchemyInsightReportRepository,
    SQLAlchemyInsightRequestRepository,
)
from alphaedge.modules.insights.infrastructure.openai_llm import OpenAILLMProvider
from alphaedge.shared.infrastructure.database import async_session_factory


def _get_llm_provider():
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAILLMProvider()
    return MockLLMProvider()


async def execute_insight(request_id: UUID) -> None:
    async with async_session_factory() as session:
        request_repo = SQLAlchemyInsightRequestRepository(session)
        report_repo = SQLAlchemyInsightReportRepository(session)

        request = await request_repo.get_by_id(request_id)
        if not request or request.status == InsightStatus.COMPLETED:
            return

        request.mark_running()
        await request_repo.update(request)
        await session.commit()

        try:
            context = await build_context(
                session,
                user_id=request.user_id,
                insight_type=request.insight_type,
                source_type=request.source_type,
                source_id=request.source_id,
            )
            template = get_prompt(request.insight_type, PROMPT_VERSION)
            prompt = render_prompt(template, context)

            llm = _get_llm_provider()
            response = await llm.complete(prompt)

            report = InsightReport.create(
                insight_request_id=request.id,
                content=response.content,
                metadata={
                    "model": response.model,
                    "prompt_version": PROMPT_VERSION,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "insight_type": request.insight_type.value,
                },
            )
            await report_repo.save(report)

            request.mark_completed()
            await request_repo.update(request)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            request = await request_repo.get_by_id(request_id)
            if request:
                request.mark_failed(str(exc))
                await request_repo.update(request)
                await session.commit()
            raise


def run_insight_sync(request_id: str) -> None:
    asyncio.run(execute_insight(UUID(request_id)))
