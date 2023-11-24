from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from proof_generation.pattern import PrettyOptions

if TYPE_CHECKING:
    from proof_generation.pattern import Pattern


#  TODO Get rif of this wrapper type
@dataclass
class Proved:
    conclusion: Pattern

    def pretty(self, opts: PrettyOptions) -> str:
        return f'⊢ {self.conclusion.pretty(opts)}'

    def __str__(self) -> str:
        return self.pretty(PrettyOptions())
