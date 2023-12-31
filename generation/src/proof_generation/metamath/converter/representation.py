from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mypy_extensions import VarArg

if TYPE_CHECKING:
    from collections.abc import Callable

    from proof_generation.pattern import Pattern


@dataclass(frozen=True)
class Notation:
    name: str
    args: tuple[str, ...]
    type_check: Callable[[VarArg(Pattern)], bool]
    callable: Callable[[VarArg(Pattern)], Pattern]

    def __call__(self, *args: Pattern) -> Pattern:
        assert self.type_check(*args), f'Invalid arguments for {self.name}'
        return self.callable(*args)


@dataclass(frozen=True)
class Axiom:
    name: str
    args: tuple[str, ...]
    type_check: Callable[[VarArg(Pattern)], bool]
    pattern: Pattern
    metavars: tuple[str, ...]


@dataclass(frozen=True)
class AxiomWithAntecedents(Axiom):
    name: str
    args: tuple[str, ...]
    type_check: Callable[[VarArg(Pattern)], bool]
    pattern: Pattern
    metavars: tuple[str, ...]
    antecedents: tuple[Pattern, ...]


@dataclass(frozen=True)
class Proof:
    labels: dict[int, str]
    applied_lemmas: list[int]


@dataclass(frozen=True)
class Lemma(Axiom):
    proof: Proof


class LemmaWithAntecedents(AxiomWithAntecedents, Lemma):
    pass
