from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from .models import CatalogAudit, CatalogEpisode, CatalogLine, CatalogPlayback
from .playback_schemas import EpisodeResponse, LineResponse
from .import_models import CatalogProvider
from .service import CatalogService


class CatalogPlaybackService(CatalogService):
    async def graph(self, db: AsyncSession, content_id: int):
        content = await self.get(db, content_id)
        episodes = list((await db.scalars(select(CatalogEpisode).where(CatalogEpisode.content_id == content_id)
            .order_by(CatalogEpisode.sort_order, CatalogEpisode.number, CatalogEpisode.id))).all())
        lines = list((await db.scalars(select(CatalogLine).where(CatalogLine.content_id == content_id)
            .order_by(CatalogLine.sort_order, CatalogLine.id))).all())
        playbacks = list((await db.scalars(select(CatalogPlayback).where(CatalogPlayback.content_id == content_id)
            .order_by(CatalogPlayback.id))).all())
        enabled_lines = {line.id for line in lines if not line.disabled}
        counts = {}
        for item in playbacks:
            if not item.disabled and item.line_id in enabled_lines and item.media_type != "page":
                counts[item.episode_id] = counts.get(item.episode_id, 0) + 1
        result = []
        for episode in episodes:
            response = EpisodeResponse.model_validate(episode)
            response.available_line_count = 0 if content.disabled or episode.disabled else counts.get(episode.id, 0)
            result.append(response)
        providers = {p.code: p for p in (await db.scalars(select(CatalogProvider).where(
            CatalogProvider.code.in_({line.source_key for line in lines})
        ))).all()}
        display_lines = []
        for line in lines:
            response = LineResponse.model_validate(line)
            provider = providers.get(line.source_key)
            response.display_name = (provider.abbreviation or provider.name) if provider else line.name
            display_lines.append(response)
        return dict(content=content, episodes=result, lines=display_lines, playbacks=playbacks)

    async def owned(self, db, model, content_id, item_id):
        item = await db.get(model, item_id)
        if item is None or item.content_id != content_id:
            raise NotFoundError("Catalog item not found", reason="catalog_item_not_found")
        return item

    async def save(self, db, model, content_id, payload, actor_id, item_id=None):
        content = await self.get(db, content_id)
        if content.version != payload.version:
            raise ConflictError("Reload the resource before editing", reason="catalog_version_conflict")
        item = await self.owned(db, model, content_id, item_id) if item_id is not None else None
        values = payload.model_dump(exclude={"version"})
        if model is CatalogPlayback:
            await self.owned(db, CatalogEpisode, content_id, payload.episode_id)
            await self.owned(db, CatalogLine, content_id, payload.line_id)
        changes = {key: {"before": getattr(item, key) if item else None, "after": value}
                   for key, value in values.items() if item is None or getattr(item, key) != value}
        if not changes:
            return await self.graph(db, content_id)
        # Lock the work through an atomic compare-and-swap before modifying any child.
        if not await self.repo.update(db, content_id, payload.version, {}):
            await db.rollback()
            raise ConflictError("Reload the resource before editing", reason="catalog_version_conflict")
        action = {CatalogEpisode: "episode", CatalogLine: "line", CatalogPlayback: "playback"}[model]
        try:
            if item is None:
                item = model(content_id=content_id, **values)
                db.add(item)
            else:
                for key, value in values.items():
                    setattr(item, key, value)
            await db.flush()
            changes["item_id"] = {"before": None, "after": item.id}
            db.add(CatalogAudit(content_id=content_id, actor_id=actor_id,
                action=f"{action}_{'create' if item_id is None else 'update'}", changes=changes))
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ConflictError("Episode, line or mapping already exists", reason="catalog_mapping_conflict") from exc
        await db.refresh(content)
        return await self.graph(db, content_id)

    async def preview(self, db, content_id, item_id):
        content = await self.get(db, content_id)
        item = await self.owned(db, CatalogPlayback, content_id, item_id)
        episode = await self.owned(db, CatalogEpisode, content_id, item.episode_id)
        line = await self.owned(db, CatalogLine, content_id, item.line_id)
        if content.disabled or episode.disabled or line.disabled or item.disabled:
            raise BadRequestError("This playback is disabled", reason="catalog_playback_disabled")
        if item.media_type == "page":
            raise BadRequestError("Player pages cannot be previewed", reason="catalog_preview_unsupported")
        # Admin preview allows drafts; it neither publishes nor fetches/proxies the URL.
        return dict(url=item.url, media_type=item.media_type)
