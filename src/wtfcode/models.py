from dataclasses import dataclass, field


@dataclass
class RepoFile:
    path: str
    degree: int
    community: str
    is_critical: bool = False
    fragility_score: float = 0.0
    connections: list[str] = field(default_factory=list)


@dataclass
class FailureScenario:
    title: str
    trigger: str
    downstream: list[str]
    severity: str  # high / medium / low
    likelihood: str
    consequence: str = ""   # the outage story: "users can't log in, 500s everywhere"
    mitigation: str = ""
    why_this_happens: str = ""   # structural root cause, max 18 words
    system_smell: str = ""       # single point of failure | high coupling | hidden dependency chain | overloaded module
    how_to_vibe_safely: str = "" # what a vibecoder must check before touching this
