from alphaedge.modules.strategy.application.commands import (
    CreateStrategyCommand,
    CreateStrategyVersionCommand,
    DeleteStrategyCommand,
    GetStrategyQuery,
    GetStrategyVersionQuery,
    IndicatorDTO,
    ListIndicatorsQuery,
    ListStrategiesQuery,
    ListStrategyVersionsQuery,
    StrategyDTO,
    StrategyVersionDTO,
    UpdateStrategyCommand,
    ValidateStrategyVersionCommand,
    ValidationResultDTO,
)
from alphaedge.modules.strategy.domain.dsl import StrategyCompiler
from alphaedge.modules.strategy.domain.repositories import (
    IndicatorRepository,
    StrategyRepository,
    StrategyVersionRepository,
)
from alphaedge.modules.strategy.domain.value_objects import Strategy, StrategyVersion
from alphaedge.shared.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    DomainException,
    NotFoundError,
)


class CreateStrategyHandler:
    def __init__(
        self,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, command: CreateStrategyCommand) -> StrategyDTO:
        existing = await self._strategy_repo.get_by_user_and_name(command.user_id, command.name)
        if existing:
            raise ConflictError(f"Strategy '{command.name}' already exists")

        strategy = Strategy.create(
            user_id=command.user_id,
            name=command.name,
            strategy_type=command.strategy_type,
            description=command.description,
        )
        saved = await self._strategy_repo.save(strategy)

        if command.source_code:
            version = StrategyVersion.create(
                strategy_id=saved.id,
                version=1,
                source_code=command.source_code,
                parameters=command.parameters,
            )
            await self._version_repo.save(version)

        return StrategyDTO.from_entity(saved)


class ListStrategiesHandler:
    def __init__(self, strategy_repo: StrategyRepository) -> None:
        self._strategy_repo = strategy_repo

    async def handle(self, query: ListStrategiesQuery) -> tuple[list[StrategyDTO], int]:
        items = await self._strategy_repo.list_by_user(
            query.user_id,
            active_only=query.active_only,
            limit=query.limit,
            offset=query.offset,
        )
        total = await self._strategy_repo.count_by_user(
            query.user_id, active_only=query.active_only
        )
        return [StrategyDTO.from_entity(s) for s in items], total


class GetStrategyHandler:
    def __init__(self, strategy_repo: StrategyRepository) -> None:
        self._strategy_repo = strategy_repo

    async def handle(self, query: GetStrategyQuery) -> StrategyDTO:
        strategy = await _get_owned_strategy(self._strategy_repo, query.user_id, query.strategy_id)
        return StrategyDTO.from_entity(strategy)


class UpdateStrategyHandler:
    def __init__(self, strategy_repo: StrategyRepository) -> None:
        self._strategy_repo = strategy_repo

    async def handle(self, command: UpdateStrategyCommand) -> StrategyDTO:
        strategy = await self._get_owned_strategy(command.user_id, command.strategy_id)
        if command.name is not None:
            strategy.name = command.name.strip()
        if command.description is not None:
            strategy.description = command.description.strip() or None
        if command.is_active is not None:
            strategy.is_active = command.is_active
        saved = await self._strategy_repo.save(strategy)
        return StrategyDTO.from_entity(saved)

    async def _get_owned_strategy(self, user_id, strategy_id) -> Strategy:
        return await _get_owned_strategy(self._strategy_repo, user_id, strategy_id)


class DeleteStrategyHandler:
    def __init__(self, strategy_repo: StrategyRepository) -> None:
        self._strategy_repo = strategy_repo

    async def handle(self, command: DeleteStrategyCommand) -> None:
        strategy = await _get_owned_strategy(
            self._strategy_repo, command.user_id, command.strategy_id
        )
        await self._strategy_repo.soft_delete(strategy)


class CreateStrategyVersionHandler:
    def __init__(
        self,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, command: CreateStrategyVersionCommand) -> StrategyVersionDTO:
        await _get_owned_strategy(self._strategy_repo, command.user_id, command.strategy_id)
        next_version = await self._version_repo.next_version_number(command.strategy_id)
        version = StrategyVersion.create(
            strategy_id=command.strategy_id,
            version=next_version,
            source_code=command.source_code,
            parameters=command.parameters,
        )
        saved = await self._version_repo.save(version)
        return StrategyVersionDTO.from_entity(saved)


class ListStrategyVersionsHandler:
    def __init__(
        self,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, query: ListStrategyVersionsQuery) -> list[StrategyVersionDTO]:
        await _get_owned_strategy(self._strategy_repo, query.user_id, query.strategy_id)
        versions = await self._version_repo.list_by_strategy(query.strategy_id)
        return [StrategyVersionDTO.from_entity(v) for v in versions]


class GetStrategyVersionHandler:
    def __init__(
        self,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, query: GetStrategyVersionQuery) -> StrategyVersionDTO:
        await _get_owned_strategy(self._strategy_repo, query.user_id, query.strategy_id)
        version = await self._version_repo.get_by_id(query.version_id)
        if not version or version.strategy_id != query.strategy_id:
            raise NotFoundError("StrategyVersion", str(query.version_id))
        return StrategyVersionDTO.from_entity(version)


class ValidateStrategyVersionHandler:
    def __init__(
        self,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, command: ValidateStrategyVersionCommand) -> ValidationResultDTO:
        strategy = await _get_owned_strategy(
            self._strategy_repo, command.user_id, command.strategy_id
        )
        version = await self._version_repo.get_by_id(command.version_id)
        if not version or version.strategy_id != command.strategy_id:
            raise NotFoundError("StrategyVersion", str(command.version_id))

        errors: list[str] = []
        try:
            _, compiled_hash = StrategyCompiler.validate_and_compile(
                strategy.strategy_type,
                version.source_code,
                strategy.name,
                version.parameters,
            )
            version.mark_validated(compiled_hash)
            await self._version_repo.save(version)
            return ValidationResultDTO(
                version_id=version.id,
                status=version.status.value,
                compiled_hash=compiled_hash,
                errors=[],
            )
        except DomainException as exc:
            errors.append(exc.message)
        except Exception as exc:
            errors.append(str(exc))
        return ValidationResultDTO(
            version_id=version.id,
            status=version.status.value,
            compiled_hash=version.compiled_hash or "",
            errors=errors,
        )


class ListIndicatorsHandler:
    def __init__(self, indicator_repo: IndicatorRepository) -> None:
        self._indicator_repo = indicator_repo

    async def handle(self, _query: ListIndicatorsQuery) -> list[IndicatorDTO]:
        items = await self._indicator_repo.list_all()
        return [IndicatorDTO.from_entity(i) for i in items]


async def _get_owned_strategy(strategy_repo: StrategyRepository, user_id, strategy_id) -> Strategy:
    strategy = await strategy_repo.get_by_id(strategy_id)
    if not strategy or strategy.deleted_at is not None:
        raise NotFoundError("Strategy", str(strategy_id))
    if strategy.user_id != user_id:
        raise AuthorizationError("You do not own this strategy")
    return strategy
