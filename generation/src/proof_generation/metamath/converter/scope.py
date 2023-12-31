from __future__ import annotations

from typing import TYPE_CHECKING

from proof_generation.metamath.ast import Metavariable
from proof_generation.metamath.converter.vardict import VarDict
from proof_generation.pattern import EVar, MetaVar, SVar

if TYPE_CHECKING:
    from proof_generation.metamath.converter.representation import Notation
    from proof_generation.pattern import Pattern


class Scope:
    """Implementation of the scope. It is a dictionary with a couple of additional methods."""

    def __init__(
        self,
    ) -> None:
        self._metavars: VarDict = VarDict(None, MetaVar)
        self._element_vars: VarDict = VarDict(None, EVar)
        self._set_vars: VarDict = VarDict(None, SVar)
        self._notations: dict[str, tuple[Notation, ...]] = {}

    def add_metavariable(self, var: Metavariable | str) -> None:
        self._metavars[var] = MetaVar(len(self._metavars))

    def supercede_metavariable(self, name: str, var: MetaVar) -> None:
        assert name in self._metavars
        assert self._metavars[name].name == var.name
        self._metavars[name] = var

    def add_element_var(self, var: Metavariable | str) -> None:
        self._element_vars[var] = EVar(len(self._element_vars))

    def add_set_var(self, var: Metavariable | str) -> None:
        self._set_vars[var] = SVar(len(self._set_vars))

    def add_notation(self, notation: Notation) -> None:
        self._notations.setdefault(notation.name, ())
        self._notations[notation.name] += (notation,)

    def resolve(self, name: str) -> Pattern:
        if name in self._metavars:
            var = self._metavars[name]
        elif name in self._element_vars:
            var = self._element_vars[name]
        elif name in self._set_vars:
            var = self._set_vars[name]
        else:
            raise KeyError(f'Unknown variable {name}')
        return var

    def resolve_notation(self, name: str, *args: Pattern) -> Notation:
        if name not in self._notations:
            raise KeyError(f'Unknown notation {name}')
        notations = self._notations[name]
        if len(notations) == 1:
            return notations[0]
        else:
            for notation in notations:
                if notation.type_check(*args):
                    return notation
            else:
                raise ValueError(f'No notation for {name} matches')

    def is_notation(self, name: str) -> bool:
        return name in self._notations

    def is_metavar(self, name: str) -> bool:
        return name in self._metavars

    def import_from_scope(self, other: Scope, except_names: None | tuple[str, ...] = None) -> None:
        self._metavars = VarDict(other._metavars)
        self._element_vars = VarDict(
            {k: v for k, v in other._element_vars.items() if except_names is None or k not in except_names}, EVar
        )
        self._set_vars = VarDict(
            {k: v for k, v in other._set_vars.items() if except_names is None or k not in except_names}, SVar
        )
        self._notations = dict(other._notations)


class GlobalScope(Scope):
    """This is a global scope where actually everything is defined. But some variables can be umbigous."""

    def __init__(self) -> None:
        super().__init__()
        self._ambiguous_vars: set[str] = set()

    def add_variable(self, var: Metavariable) -> None:
        self._ambiguous_vars.add(var.name)
        self.add_element_var(var)
        self.add_set_var(var)

    def is_ambiguous(self, name: str | Metavariable) -> bool:
        return name in self._ambiguous_vars if isinstance(name, str) else name.name in self._ambiguous_vars

    def unambiguize(self, selelcted_vars: tuple[str, ...]) -> tuple[Scope, ...]:
        assert all(var in self._ambiguous_vars for var in selelcted_vars)

        todo: list[Scope] = [self]
        scopes: list[Scope | GlobalScope] = []
        variables = sorted(selelcted_vars)

        if not variables:
            scope = Scope()
            scope.import_from_scope(self)
            return (scope,)

        while variables:
            scopes = []
            var: str = variables.pop()

            for scope in todo:
                new_scope1 = Scope()
                new_scope1.import_from_scope(scope, except_names=tuple(variables + [var]))
                new_scope1.add_element_var(var)

                new_scope2 = Scope()
                new_scope2.import_from_scope(scope, except_names=tuple(variables + [var]))
                new_scope2.add_set_var(var)

                scopes.append(new_scope1)
                scopes.append(new_scope2)

            todo = scopes
        return tuple(todo)


class NotationScope(Scope):
    """
    This is a scope used for translating notations. The difference is that some variables arn't resolved but used as arguments
    """

    def __init__(self, arguments: tuple[str, ...]) -> None:
        self._args: tuple[str, ...] = arguments
        super().__init__()

    @property
    def arguments(self) -> tuple[str, ...]:
        return self._args

    def is_arg(self, name: str) -> int | None:
        if name in self._args:
            return self._args.index(name)
        else:
            return None


def to_notation_scope(current_scope: Scope, args: tuple[Metavariable, ...]) -> NotationScope:
    assert all(isinstance(arg, Metavariable) for arg in args)
    arg_names: tuple[str, ...] = tuple(arg.name for arg in args)
    new = NotationScope(arg_names)
    new.import_from_scope(current_scope)
    return new
