from sqlalchemy import select, func, update

from app.core.exceptions import ConflictError
from .import_models import CatalogSource
from .models import CatalogContent, CatalogEpisode, CatalogLine, CatalogPlayback, CatalogAudit
from .repository import CatalogRepository


def merge_fields(item, incoming, previous):
    """Only replace fields that still equal the last imported value."""
    changes = {}
    for key, value in incoming.items():
        old = getattr(item, key)
        if key in previous and old == previous[key] and old != value:
            setattr(item, key, value)
            changes[key] = {"before": old, "after": value}
    return changes


async def sync_work(db, provider, upstream_id, fields, entries, actor_id, target_id=None):
    source = await db.scalar(select(CatalogSource).where(
        CatalogSource.provider_id == provider.id, CatalogSource.upstream_id == upstream_id))
    if source is not None and target_id is not None and source.content_id != target_id:
        raise ConflictError("Source mapping changed", reason="catalog_version_conflict")
    created = source is None and target_id is None
    changes = {}
    if created:
        content = CatalogContent(**fields)
        db.add(content)
        await db.flush()
        source = CatalogSource(provider_id=provider.id, upstream_id=upstream_id, content_id=content.id, snapshot={})
        db.add(source)
        changes["import_content"] = {"before": None, "after": content.id}
    else:
        content = await db.get(CatalogContent, source.content_id if source else target_id)
        if content is None:
            raise ConflictError("Content removed", reason="catalog_version_conflict")
        if content.disabled:
            return dict(status="skipped", reason="work_disabled", content_id=content.id, entries=0)
        # Import and manual edits serialize against the same content version.
        if not await CatalogRepository().update(db, content.id, content.version, {}):
            raise ConflictError("Concurrent catalog edit", reason="catalog_version_conflict")
        if source is None:
            source = CatalogSource(provider_id=provider.id, upstream_id=upstream_id, content_id=content.id, snapshot={})
            db.add(source)
            changes["import_content"] = {"before": None, "after": content.id}
        else:
            changes.update(merge_fields(content, fields, source.snapshot.get("content", {})))
    old_entries = source.snapshot.get("entries", {})
    new_entries = dict(old_entries)  # Missing upstream entries are retained, never deleted implicitly.
    episodes = {item.id: item for item in (await db.scalars(select(CatalogEpisode).where(CatalogEpisode.content_id == content.id))).all()}
    lines = {item.id: item for item in (await db.scalars(select(CatalogLine).where(CatalogLine.content_id == content.id))).all()}
    playbacks = {item.id: item for item in (await db.scalars(select(CatalogPlayback).where(CatalogPlayback.content_id == content.id))).all()}
    change_count = 0
    incoming_keys = {entry['key'] for entry in entries}
    reused_keys = set()
    for entry in entries:
        old = old_entries.get(entry["key"], {})
        if not old:
            # A recap's inferred number can change from x.5 to x.51 when a
            # second recap is added. Reuse its stable playback/episode IDs.
            matches = [(key, snapshot) for key, snapshot in old_entries.items()
                       if key not in incoming_keys and key not in reused_keys
                       and snapshot.get('line', {}).get('line_key') == entry['line']
                       and snapshot.get('playback', {}).get('url') == entry['url']]
            if len(matches) == 1:
                previous_key, old = matches[0]
                reused_keys.add(previous_key)
                new_entries.pop(previous_key, None)
        episode_fields = dict(title=entry["title"], kind=entry["kind"], number=entry["number"], sort_order=entry["number"])
        episode = episodes.get(old.get("episode_id"))
        if episode is None:
            episode = next((x for x in episodes.values() if x.kind == entry["kind"] and x.number == entry["number"]), None)
        if episode is None:
            episode = CatalogEpisode(content_id=content.id, **episode_fields)
            db.add(episode)
            await db.flush()
            episodes[episode.id] = episode
            change_count += 1
        elif not episode.disabled:
            change_count += bool(merge_fields(episode, episode_fields, old.get("episode", {})))
        line_fields = dict(name=provider.name, source_key=provider.code, line_key=entry["line"], sort_order=0)
        line = lines.get(old.get("line_id"))
        if line is None:
            line = next((x for x in lines.values() if x.source_key == provider.code and x.line_key == entry["line"]), None)
        if line is None:
            line = CatalogLine(content_id=content.id, **line_fields)
            db.add(line)
            await db.flush()
            lines[line.id] = line
            change_count += 1
        elif not line.disabled:
            change_count += bool(merge_fields(line, line_fields, old.get("line", {})))
        playback_fields = dict(url=entry["url"], media_type="hls", source_label=entry["title"])
        playback = playbacks.get(old.get("playback_id"))
        if playback is None:
            playback = next((x for x in playbacks.values() if x.episode_id == episode.id and x.line_id == line.id), None)
        if playback is None:
            playback = CatalogPlayback(content_id=content.id, episode_id=episode.id, line_id=line.id, **playback_fields)
            db.add(playback)
            await db.flush()
            playbacks[playback.id] = playback
            change_count += 1
        elif not playback.disabled and not episode.disabled and not line.disabled:
            # A manually remapped entry must not be pulled back to its former episode/line.
            if playback.episode_id == episode.id and playback.line_id == line.id:
                change_count += bool(merge_fields(playback, playback_fields, old.get("playback", {})))
        new_entries[entry["key"]] = dict(episode_id=episode.id, line_id=line.id, playback_id=playback.id,
            episode=episode_fields, line=line_fields, playback=playback_fields)
    source.snapshot = dict(content=fields, entries=new_entries)
    source.updated_at = func.now()
    if change_count:
        changes["import_items"] = {"before": None, "after": change_count}
    if changes:
        changes["upstream_id"] = {"before": None, "after": upstream_id}
        db.add(CatalogAudit(content_id=content.id, actor_id=actor_id, action="import_create" if created else "import_update", changes=changes))
    # A no-op reimport must not invalidate an editor. The CAS above held the write lock.
    if not created and not changes:
        await db.execute(update(CatalogContent).where(CatalogContent.id == content.id)
                         .values(version=content.version, updated_at=content.updated_at))
    return dict(status="created" if created else "updated" if changes else "unchanged", reason="", content_id=content.id, entries=len(entries))
