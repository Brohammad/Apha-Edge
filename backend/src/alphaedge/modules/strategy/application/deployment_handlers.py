"""Application handlers for strategy deployments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.execution.domain.repositories import BrokerConnectionRepository
from alphaedge.modules.portfolio.domain.repositories import PortfolioRepository
from alphaedge.modules.strategy.domain.deployment import StrategyDeployment, require_validated_version
from alphaedge.modules.strategy.domain.repositories import (
    StrategyDeploymentRepository,
    StrategyRepository,
    StrategyVersionRepository,
)
from alphaedge.modules.strategy.infrastructure.deployment_runner import pause_deployment
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError


@dataclass(frozen=True)
class CreateDeploymentCommand:
    user_id: UUID
    strategy_version_id: UUID
    portfolio_id: UUID
    broker_connection_id: UUID
    instrument_ids: list[UUID]
    quantity: str


@dataclass(frozen=True)
class ListDeploymentsQuery:
    user_id: UUID


@dataclass(frozen=True)
class PauseDeploymentCommand:
    user_id: UUID
    deployment_id: UUID


@dataclass(frozen=True)
class ResumeDeploymentCommand:
    user_id: UUID
    deployment_id: UUID


@dataclass(frozen=True)
class DeploymentDTO:
    id: UUID
    user_id: UUID
    strategy_version_id: UUID
    portfolio_id: UUID
    broker_connection_id: UUID
    instrument_ids: list[str]
    quantity: str
    is_active: bool
    last_signal_at: datetime | None
    last_signal_action: str | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: StrategyDeployment) -> DeploymentDTO:
        return DeploymentDTO(
            id=entity.id,
            user_id=entity.user_id,
            strategy_version_id=entity.strategy_version_id,
            portfolio_id=entity.portfolio_id,
            broker_connection_id=entity.broker_connection_id,
            instrument_ids=[str(i) for i in entity.instrument_ids],
            quantity=str(entity.quantity),
            is_active=entity.is_active,
            last_signal_at=entity.last_signal_at,
            last_signal_action=entity.last_signal_action,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class CreateDeploymentHandler:
    def __init__(
        self,
        deployment_repo: StrategyDeploymentRepository,
        version_repo: StrategyVersionRepository,
        strategy_repo: StrategyRepository,
        portfolio_repo: PortfolioRepository,
        connection_repo: BrokerConnectionRepository,
    ) -> None:
        self._deployment_repo = deployment_repo
        self._version_repo = version_repo
        self._strategy_repo = strategy_repo
        self._portfolio_repo = portfolio_repo
        self._connection_repo = connection_repo

    async def handle(self, command: CreateDeploymentCommand) -> DeploymentDTO:
        version = await self._version_repo.get_by_id(command.strategy_version_id)
        if not version:
            raise NotFoundError("StrategyVersion", str(command.strategy_version_id))
        strategy = await self._strategy_repo.get_by_id(version.strategy_id)
        if not strategy or strategy.user_id != command.user_id:
            raise AuthorizationError("You do not own this strategy version")
        require_validated_version(version.status)

        portfolio = await self._portfolio_repo.get_by_id(command.portfolio_id)
        if not portfolio or portfolio.user_id != command.user_id:
            raise NotFoundError("Portfolio", str(command.portfolio_id))

        connection = await self._connection_repo.get_by_id(command.broker_connection_id)
        if not connection or connection.user_id != command.user_id:
            raise NotFoundError("BrokerConnection", str(command.broker_connection_id))
        if not connection.is_paper:
            raise ValidationError("Strategy deployments currently require a paper broker connection")

        qty = Decimal(command.quantity)
        deployment = StrategyDeployment.create(
            user_id=command.user_id,
            strategy_version_id=command.strategy_version_id,
            portfolio_id=command.portfolio_id,
            broker_connection_id=command.broker_connection_id,
            instrument_ids=command.instrument_ids,
            quantity=qty,
        )
        saved = await self._deployment_repo.save(deployment)
        return DeploymentDTO.from_entity(saved)


class ListDeploymentsHandler:
    def __init__(self, deployment_repo: StrategyDeploymentRepository) -> None:
        self._deployment_repo = deployment_repo

    async def handle(self, query: ListDeploymentsQuery) -> list[DeploymentDTO]:
        items = await self._deployment_repo.list_by_user(query.user_id)
        return [DeploymentDTO.from_entity(d) for d in items]


class PauseDeploymentHandler:
    def __init__(self, deployment_repo: StrategyDeploymentRepository) -> None:
        self._deployment_repo = deployment_repo

    async def handle(self, command: PauseDeploymentCommand) -> DeploymentDTO:
        deployment = await _get_owned_deployment(
            self._deployment_repo, command.user_id, command.deployment_id
        )
        deployment.pause()
        saved = await self._deployment_repo.save(deployment)
        await pause_deployment(deployment.id)
        return DeploymentDTO.from_entity(saved)


class ResumeDeploymentHandler:
    def __init__(self, deployment_repo: StrategyDeploymentRepository) -> None:
        self._deployment_repo = deployment_repo

    async def handle(self, command: ResumeDeploymentCommand) -> DeploymentDTO:
        deployment = await _get_owned_deployment(
            self._deployment_repo, command.user_id, command.deployment_id
        )
        deployment.resume()
        saved = await self._deployment_repo.save(deployment)
        return DeploymentDTO.from_entity(saved)


async def _get_owned_deployment(
    repo: StrategyDeploymentRepository, user_id: UUID, deployment_id: UUID
) -> StrategyDeployment:
    deployment = await repo.get_by_id(deployment_id)
    if not deployment:
        raise NotFoundError("StrategyDeployment", str(deployment_id))
    if deployment.user_id != user_id:
        raise AuthorizationError("You do not own this deployment")
    return deployment
