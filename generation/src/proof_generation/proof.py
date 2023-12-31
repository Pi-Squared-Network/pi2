from __future__ import annotations

from argparse import ArgumentParser
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from proof_generation.claim import Claim
from proof_generation.counting_interpreter import CountingInterpreter
from proof_generation.interpreter import ExecutionPhase
from proof_generation.optimizing_interpreters import MemoizingInterpreter
from proof_generation.pattern import ESubst, EVar, Exists, Implies, PrettyOptions, bot, phi0, phi1, phi2
from proof_generation.pretty_printing_interpreter import PrettyPrintingInterpreter
from proof_generation.proved import Proved
from proof_generation.serializing_interpreter import SerializingInterpreter

if TYPE_CHECKING:
    from collections.abc import Callable

    from proof_generation.interpreter import Interpreter
    from proof_generation.pattern import Notation, Pattern
    from proof_generation.serializing_interpreter import IOInterpreter


class OutputFormat(str, Enum):
    Binary = 'binary'
    Pretty = 'pretty'


# Proof Expressions
# =================


class ProofThunk:
    _expr: Callable[[Interpreter], Proved]
    conc: Pattern

    def __init__(self, expr: Callable[[Interpreter], Proved], conc: Pattern):
        self._expr = expr
        self.conc = conc

    def __call__(self, interpreter: Interpreter) -> Proved:
        proved = self._expr(interpreter)
        # TODO Check is this call to equality is causing performance issues
        assert proved.conclusion == self.conc
        return proved


class ProofExp:
    _axioms: list[Pattern]
    _notations: list[Notation]
    _claims: list[Pattern]
    _proof_expressions: list[ProofThunk]

    _submodules: list[ProofExp]

    def __init__(
        self,
        axioms: list[Pattern] | None = None,
        notations: list[Notation] | None = None,
        claims: list[Pattern] | None = None,
        proof_expressions: list[ProofThunk] | None = None,
    ) -> None:
        self._axioms = [] if axioms is None else axioms
        self._notations = [] if notations is None else notations
        self._claims = [] if claims is None else claims
        self._proof_expressions = [] if proof_expressions is None else proof_expressions
        self._submodules = []

    def add_axiom(self, axiom: Pattern) -> None:
        if axiom not in self._axioms:
            self._axioms.append(axiom)

    def add_assumption(self, axiom: Pattern) -> None:
        self.add_axiom(axiom)

    def add_axioms(self, axioms: list[Pattern]) -> None:
        for axiom in axioms:
            self.add_axiom(axiom)

    def add_assumptions(self, axioms: list[Pattern]) -> None:
        self.add_axioms(axioms)

    def get_axioms(self) -> list[Pattern]:
        return list(self._axioms)  # Avoid reference leaking

    def add_notation(self, notation: Notation) -> None:
        if notation not in self._notations:
            self._notations.append(notation)

    def add_notations(self, notations: list[Notation]) -> None:
        for notation in notations:
            self.add_notation(notation)

    def get_notations(self) -> list[Notation]:
        return list(self._notations)  # Avoid reference leaking

    def add_claim(self, claim: Pattern) -> None:
        assert claim not in self._claims
        self._claims.append(claim)

    def add_claims(self, claims: list[Pattern]) -> None:
        for claim in claims:
            self.add_claim(claim)

    def get_claims(self) -> list[Pattern]:
        return list(self._claims)  # Avoid reference leaking

    def add_proof_expression(self, proof_expression: ProofThunk) -> None:
        assert proof_expression not in self._proof_expressions
        self._proof_expressions.append(proof_expression)

    def add_proof_expressions(self, proof_expressions: list[ProofThunk]) -> None:
        for proof_expression in proof_expressions:
            self.add_proof_expression(proof_expression)

    def get_proof_expressions(self) -> list[ProofThunk]:
        return list(self._proof_expressions)  # Avoid reference leaking

    ProofExpTypeVar = TypeVar('ProofExpTypeVar', bound='ProofExp')

    def import_module(self, module: ProofExpTypeVar) -> ProofExpTypeVar:
        self._submodules.append(module)
        self.add_notations(module.get_notations())
        return module

    # Proof Rules
    # -----------

    def dynamic_inst(self, pf: ProofThunk, delta: dict[int, Pattern]) -> ProofThunk:
        if not delta:
            return pf

        def proved_exp(interpreter: Interpreter) -> Proved:
            for idn, p in delta.items():
                delta[idn] = interpreter.pattern(p)
            return interpreter.instantiate(pf(interpreter), delta)

        return ProofThunk(proved_exp, pf.conc.instantiate(delta))

    def prop1(self) -> ProofThunk:
        return ProofThunk((lambda interpreter: interpreter.prop1()), Implies(phi0, Implies(phi1, phi0)))

    def prop2(self) -> ProofThunk:
        return ProofThunk(
            (lambda interpreter: interpreter.prop2()),
            Implies(Implies(phi0, Implies(phi1, phi2)), Implies(Implies(phi0, phi1), Implies(phi0, phi2))),
        )

    def prop3(self) -> ProofThunk:
        return ProofThunk(
            (lambda interpreter: interpreter.prop3()), Implies(Implies(Implies(phi0, bot()), bot()), phi0)
        )

    def modus_ponens(self, left: ProofThunk, right: ProofThunk) -> ProofThunk:
        p, q = Implies.extract(left.conc)
        assert p == right.conc
        return ProofThunk((lambda interpreter: interpreter.modus_ponens(left(interpreter), right(interpreter))), q)

    def exists_quantifier(self) -> ProofThunk:
        x = EVar(0)
        y = EVar(1)
        return ProofThunk(
            (lambda interpreter: interpreter.exists_quantifier()), Implies(ESubst(phi0, x, y), Exists(x.name, phi0))
        )

    def exists_generalization(self, proved: ProofThunk, var: EVar) -> ProofThunk:
        l, r = Implies.extract(proved.conc)
        return ProofThunk(
            (lambda interpreter: interpreter.exists_generalization(proved(interpreter), var)),
            Implies(Exists(var.name, l), r),
        )

    def instantiate(self, proved: ProofThunk, delta: dict[int, Pattern]) -> ProofThunk:
        return ProofThunk(
            (lambda interpreter: interpreter.instantiate(proved(interpreter), delta)), proved.conc.instantiate(delta)
        )

    def load_axiom(self, axiom_term: Pattern) -> ProofThunk:
        assert axiom_term in self._axioms
        axiom = Proved(axiom_term)

        def proved_exp(interpreter: Interpreter) -> Proved:
            interpreter.load(f'Axiom {str(axiom)}', axiom)
            return axiom

        return ProofThunk(proved_exp, axiom_term)

    # TODO: Remove this method once it's no longer used. It is dangerous
    def load_axiom_by_index(self, i: int) -> ProofThunk:
        return self.load_axiom(self._axioms[i])

    def publish_proof(self, proved: ProofThunk) -> ProofThunk:
        def proved_exp(interpreter: Interpreter) -> Proved:
            interpreter.publish_proof(proved(interpreter))
            return Proved(proved.conc)

        return ProofThunk(proved_exp, proved.conc)

    def execute_gamma_phase(self, interpreter: Interpreter, move_into_claim: bool = True) -> None:
        assert interpreter.phase == ExecutionPhase.Gamma
        for submodule in self._submodules:
            submodule.execute_gamma_phase(interpreter, False)
        for axiom in self._axioms:
            interpreter.publish_axiom(interpreter.pattern(axiom))
        self.check_interpreting(interpreter)
        if move_into_claim:
            interpreter.into_claim_phase()

    def execute_claims_phase(self, interpreter: Interpreter, move_into_proof: bool = True) -> None:
        assert interpreter.phase == ExecutionPhase.Claim
        for claim in reversed(self._claims):
            interpreter.publish_claim(interpreter.pattern(claim))
        self.check_interpreting(interpreter)
        if move_into_proof:
            interpreter.into_proof_phase()

    def execute_proofs_phase(self, interpreter: Interpreter) -> None:
        assert interpreter.phase == ExecutionPhase.Proof
        for proof_expr in self._proof_expressions:
            self.publish_proof(proof_expr)(interpreter)
        self.check_interpreting(interpreter)

    def execute_full(self, interpreter: Interpreter) -> None:
        assert interpreter.phase == ExecutionPhase.Gamma, f'Unexpected interpreter phase: {interpreter.phase}'
        self.execute_gamma_phase(interpreter)
        self.execute_claims_phase(interpreter)
        self.execute_proofs_phase(interpreter)

    def check_interpreting(self, interpreter: Interpreter) -> None:
        if not interpreter.safe_interpreting:
            print(f'Proof generation during {interpreter.phase.name} phase is potentially unsafe!')
            for warning in interpreter.interpreting_warnings:
                print(warning)

    def pretty_options(self) -> PrettyOptions:
        return PrettyOptions(notations={n.definition: n for n in self._notations})

    def get_serializing_interpreter(
        self,
        output_format: OutputFormat,
        phase: ExecutionPhase,
        claims: list[Claim],
        file_path: Path,
    ) -> IOInterpreter:
        serializer: IOInterpreter
        match output_format:
            case OutputFormat.Binary:
                serializer = SerializingInterpreter(
                    phase=phase,
                    claims=claims,
                    out=open(file_path.with_suffix('.ml-gamma'), 'wb'),
                    claim_out=open(file_path.with_suffix('.ml-claim'), 'wb'),
                    proof_out=open(file_path.with_suffix('.ml-proof'), 'wb'),
                )
            case OutputFormat.Pretty:
                serializer = PrettyPrintingInterpreter(
                    phase=phase,
                    claims=claims,
                    out=open(file_path.with_suffix('.pretty-gamma'), 'w'),
                    claim_out=open(file_path.with_suffix('.pretty-claim'), 'w'),
                    proof_out=open(file_path.with_suffix('.pretty-proof'), 'w'),
                    pretty_options=self.pretty_options(),
                )
        return serializer

    # TODO: Implement the optimization pipeline specified in Issue #374
    # TODO: add InstantiationOptimizer
    def serialize(self, file_path: Path, output_format: OutputFormat, optimize: bool) -> None:
        claims = [Claim(claim) for claim in self._claims]
        serializer = self.get_serializing_interpreter(output_format, ExecutionPhase.Gamma, claims, file_path)
        if optimize:
            analyzer = CountingInterpreter(ExecutionPhase.Gamma, claims)
            self.execute_full(analyzer)
            self.execute_full(MemoizingInterpreter(serializer, analyzer.finalize()))
        else:
            self.execute_full(serializer)

    def main(self, argv: list[str]) -> None:
        argparser = ArgumentParser(
            prog='Proof Expression Serializer',
            description='This method outputs the ProofExp in a verifier-checkable binary format or a human-readable pretty-printed format.',
        )
        argparser.add_argument(
            'module',
            type=str,
            help='The module or script invoking this method',
        )
        argparser.add_argument(
            'output_format',
            type=OutputFormat,
            help='The proof output format, which can either be binary or pretty-printed',
        )
        argparser.add_argument('output_dir', type=str, help='The path to the output directory')
        argparser.add_argument('slice_name', type=str, help='The input slice name')
        argparser.add_argument(
            '--optimize', action='store_true', default=False, help='Optimize the proof before serializing it to output'
        )
        args = argparser.parse_args(argv)

        output_dir = Path(args.output_dir)
        if not output_dir.exists():
            print('Creating output directory...')
            output_dir.mkdir()

        self.serialize(output_dir / args.slice_name, args.output_format, args.optimize)
