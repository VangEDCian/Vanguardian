from apps.crf.infrastructure.repositories import DjangoCrfFieldLookupRepository


class CrfFieldLookupQueryService:
    repository_class = DjangoCrfFieldLookupRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def search_values(self, *, lookup_key: str, query: str = "", limit: int = 20) -> list[dict]:
        normalized_lookup_key = str(lookup_key or "").strip()
        if not normalized_lookup_key:
            return []
        normalized_query = str(query or "").strip()
        return self.repository.search_values(
            lookup_key=normalized_lookup_key,
            query=normalized_query,
            limit=limit,
        )
