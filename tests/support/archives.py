"""Fábrica de Artifacts sintéticos para os testes de privacidade.

Os testes de US4 não precisam de repositórios reais: o que está em risco é a
filtragem, não a observação. Um Artifact sintético carrega tudo o que um
vazamento vazaría — nome de cliente, URL, locator, caminho de evidência,
hash de conteúdo.
"""

from core import store

PRIVATE_ID = "root-privado1"
PUBLIC_ID = "root-publico1"
CLIENT_NAME = "client-x"
CLIENT_URL = "https://github.com/acme/client-x"
EVIDENCE_PATH = "clientx/api/deploy.yml"
CONTENT_HASH = "deadbeef" * 8


def artifact(
    artifact_id: str,
    *,
    name: str | None = None,
    visibility: str = store.VISIBILITY_PUBLIC,
    tools=(),
    techniques=(),
    sources=(),
    authorship=(),
    activity=None,
    description: str | None = None,
    content_hashes: dict | None = None,
    last_seen: str | None = None,
) -> store.Artifact:
    return store.Artifact(
        id=artifact_id,
        identity={"method": "root-commit", "value": artifact_id},
        name=name or artifact_id,
        description=description,
        visibility=visibility,
        tools=[{"name": t} for t in tools],
        techniques=list(techniques),
        dependencies=[],
        sources=[
            s if isinstance(s, store.Source)
            else store.Source(
                first_seen="2026-01-01",
                **{"last_seen": "2026-01-01", **s},
            )
            for s in sources
        ],
        activity=activity if activity is not None else {"first": "2021-03-01", "last": "2023-06-30"},
        authorship=list(authorship),
        content_hashes=content_hashes if content_hashes is not None else {},
        last_seen=last_seen,
    )


def private(**kwargs) -> store.Artifact:
    """O Artifact que, se vazar, quebra a NDA."""
    return artifact(
        PRIVATE_ID,
        name=f"repo-{CLIENT_NAME}",
        description=f"Internal tooling for {CLIENT_NAME}",
        visibility=store.VISIBILITY_PRIVATE,
        tools=("Rust", "Kafka"),
        techniques=[{
            "name": "Feature flags",
            "confidence": 0.7,
            "evidence": [EVIDENCE_PATH],
        }],
        sources=[{
            "kind": "local",
            "locator": f"/media/backup/work/{CLIENT_NAME}",
            "visibility": store.VISIBILITY_PRIVATE,
            "last_seen": "2026-07-01",
        }],
        content_hashes={EVIDENCE_PATH: CONTENT_HASH},
        last_seen="2026-07-01",
        **kwargs,
    )


def public() -> store.Artifact:
    return artifact(
        PUBLIC_ID,
        name="dendrograph",
        description="A knowledge graph of what you have built.",
        tools=("Python",),
        techniques=[{"name": "Zero runtime deps", "confidence": 0.9, "evidence": ["pyproject.toml"]}],
        sources=[{
            "kind": "github",
            "locator": "https://github.com/author/dendrograph",
            "visibility": store.VISIBILITY_PUBLIC,
        }],
        last_seen="2026-08-20",
    )


def write(root, *artifacts) -> None:
    for entry in artifacts:
        store.write(entry, root)
