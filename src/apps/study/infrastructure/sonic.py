import asyncio

from django.conf import settings


class SonicStudySiteAdapter:
    def index_study(self, *, study_id: int, code: str, name: str, sponsor: str, description: str) -> None:
        if not self._is_enabled():
            return
        text = self._build_text(code, name, sponsor, description)
        if not text:
            return
        self._push_object(bucket=settings.SONIC_BUCKET_STUDIES, object_key=self._study_object_key(study_id), text=text)

    def remove_study(self, *, study_id: int) -> None:
        if not self._is_enabled():
            return
        self._flush_object(bucket=settings.SONIC_BUCKET_STUDIES, object_key=self._study_object_key(study_id))

    def index_site(self, *, site_id: int, code: str, name: str, investigator: str) -> None:
        if not self._is_enabled():
            return
        text = self._build_text(code, name, investigator)
        if not text:
            return
        self._push_object(bucket=settings.SONIC_BUCKET_SITES, object_key=self._site_object_key(site_id), text=text)

    def remove_site(self, *, site_id: int) -> None:
        if not self._is_enabled():
            return
        self._flush_object(bucket=settings.SONIC_BUCKET_SITES, object_key=self._site_object_key(site_id))

    def _push_object(self, *, bucket: str, object_key: str, text: str) -> None:
        if not self._is_enabled():
            return
        try:
            asyncio.run(self._push_object_async(bucket=bucket, object_key=object_key, text=text))
        except RuntimeError as ex:
            print(f"[SonicStudySiteAdapter] RuntimeError during asyncio.run: {ex}")
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._push_object_async(bucket=bucket, object_key=object_key, text=text))
            finally:
                loop.close()
        except Exception as e:
            print(f"[SonicStudySiteAdapter] Exception during asyncio.run: {e}")
            return

    def _flush_object(self, *, bucket: str, object_key: str) -> None:
        if not self._is_enabled():
            return
        try:
            asyncio.run(self._flush_object_async(bucket=bucket, object_key=object_key))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._flush_object_async(bucket=bucket, object_key=object_key))
            finally:
                loop.close()
        except Exception:
            return

    async def _push_object_async(self, *, bucket: str, object_key: str, text: str) -> None:
        try:
            from asonic import Client
            from asonic.channel import IngestChannel
        except Exception:
            return

        try:
            client = Client(
                host=settings.SONIC_HOST,
                port=settings.SONIC_PORT,
                password=settings.SONIC_PASSWORD,
            )
            async with client:
                channel = await client.channel(IngestChannel)
                await channel.push(settings.SONIC_COLLECTION, bucket, object_key, text)
        except Exception:
            return

    async def _flush_object_async(self, *, bucket: str, object_key: str) -> None:
        try:
            from asonic import Client
            from asonic.channel import IngestChannel
        except Exception:
            return

        try:
            client = Client(
                host=settings.SONIC_HOST,
                port=settings.SONIC_PORT,
                password=settings.SONIC_PASSWORD,
            )
            async with client:
                channel = await client.channel(IngestChannel)
                await channel.flusho(settings.SONIC_COLLECTION, bucket, object_key)
        except Exception:
            return

    @staticmethod
    def _build_text(*parts: str) -> str:
        values: list[str] = []
        for part in parts:
            normalized = str(part or "").strip()
            if normalized:
                values.append(normalized)
        return " ".join(values)

    @staticmethod
    def _study_object_key(study_id: int) -> str:
        return f"study:{study_id}"

    @staticmethod
    def _site_object_key(site_id: int) -> str:
        return f"site:{site_id}"

    @staticmethod
    def _is_enabled() -> bool:
        return bool(getattr(settings, "SONIC_ENABLED", False))


__all__ = ["SonicStudySiteAdapter"]
