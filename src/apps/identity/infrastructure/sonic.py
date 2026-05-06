import asyncio
import re
from collections.abc import Iterable

from django.conf import settings


class SonicSearchAdapter:
    def search_study_ids(self, *, query: str, limit: int | None = None) -> list[int] | None:
        return self._search_ids(
            bucket=settings.SONIC_BUCKET_STUDIES,
            query=query,
            limit=limit,
        )

    def search_site_ids(self, *, query: str, limit: int | None = None) -> list[int] | None:
        return self._search_ids(
            bucket=settings.SONIC_BUCKET_SITES,
            query=query,
            limit=limit,
        )

    def _search_ids(self, *, bucket: str, query: str, limit: int | None = None) -> list[int] | None:
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return []
        if not getattr(settings, "SONIC_ENABLED", False):
            return None
        max_limit = int(limit or settings.SONIC_SEARCH_LIMIT or 200)
        try:
            return asyncio.run(self._search_ids_async(bucket=bucket, query=normalized_query, limit=max_limit))
        except RuntimeError:
            # Fallback when an event loop is already running.
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._search_ids_async(bucket=bucket, query=normalized_query, limit=max_limit))
            finally:
                loop.close()
        except Exception:
            return None

    async def _search_ids_async(self, *, bucket: str, query: str, limit: int) -> list[int] | None:
        try:
            from asonic import Client
            from asonic.channel import SearchChannel
        except Exception:
            return None

        try:
            client = Client(
                host=settings.SONIC_HOST,
                port=settings.SONIC_PORT,
                password=settings.SONIC_PASSWORD,
            )
            async with client:
                channel = await client.channel(SearchChannel)
                result = await channel.query(
                    collection=settings.SONIC_COLLECTION,
                    bucket=bucket,
                    terms=query,
                    limit=limit,
                    lang=settings.SONIC_LANGUAGE,
                )
        except Exception:
            return None

        return self._extract_ids(result)

    @staticmethod
    def _extract_ids(result: object) -> list[int]:
        if not isinstance(result, Iterable) or isinstance(result, (str, bytes)):
            return []
        ids: list[int] = []
        seen_ids: set[int] = set()
        for item in result:
            matched = re.search(r"(\d+)$", str(item or "").strip())
            if not matched:
                continue
            item_id = int(matched.group(1))
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            ids.append(item_id)
        return ids
