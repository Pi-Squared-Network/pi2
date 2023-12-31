from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from proof_generation.claim import Claim
from proof_generation.interpreter import ExecutionPhase
from proof_generation.metamath.converter.converter import MetamathConverter
from proof_generation.metamath.converter.representation import AxiomWithAntecedents
from proof_generation.metamath.parser import load_database
from proof_generation.metamath.translate import convert_to_implication, exec_proof
from proof_generation.pattern import Implies, MetaVar
from proof_generation.proof import ProofExp
from proof_generation.proved import Proved
from proof_generation.stateful_interpreter import StatefulInterpreter

if TYPE_CHECKING:
    from pytest import FixtureRequest

    from proof_generation.interpreter import Interpreter
    from proof_generation.metamath.parser import Database

BENCHMARK_LOCATION = 'generation/mm-benchmarks'


@pytest.fixture
def parsed_impreflex_database() -> Database:
    return load_database(os.path.join(BENCHMARK_LOCATION, 'impreflex.mm'), include_proof=True)


@pytest.fixture
def parsed_impreflex_compressed_database() -> Database:
    return load_database(os.path.join(BENCHMARK_LOCATION, 'impreflex-compressed.mm'), include_proof=True)


@pytest.fixture
def parsed_transfer_database() -> Database:
    return load_database(os.path.join(BENCHMARK_LOCATION, 'transfer-simple-goal.mm'), include_proof=True)


@pytest.fixture
def parsed_transfer_compressed_database() -> Database:
    return load_database(os.path.join(BENCHMARK_LOCATION, 'transfer-simple-compressed-goal.mm'), include_proof=True)


@pytest.mark.parametrize('db', ['parsed_impreflex_database', 'parsed_impreflex_compressed_database'])
def test_exec_proof_impreflex(db: str, request: FixtureRequest) -> None:
    converter = MetamathConverter(request.getfixturevalue(db))
    assert converter

    extracted_axioms = [converter.get_axiom_by_name(axiom_name).pattern for axiom_name in converter.exported_axioms]
    extracted_claims = [converter.get_lemma_by_name(lemma_name).pattern for lemma_name in converter.lemmas]

    # TODO: Extract this code in transfer.py to a function

    class TranslatedProofSkeleton(ProofExp):
        def __init__(self) -> None:
            super().__init__(axioms=extracted_axioms, claims=extracted_claims)

        def execute_proofs_phase(self, interpreter: Interpreter) -> None:
            assert interpreter.phase == ExecutionPhase.Proof
            exec_proof(converter, 'imp-reflexivity', self, interpreter)

    proofexp = TranslatedProofSkeleton()
    interpreter = StatefulInterpreter(
        ExecutionPhase.Gamma,
        [Claim(claim) for claim in extracted_claims],
    )
    proofexp.execute_full(interpreter)

    assert interpreter.stack == [Proved(Implies(MetaVar(0), MetaVar(0)))]


@pytest.mark.parametrize('db', ['parsed_transfer_database', 'parsed_transfer_compressed_database'])
def test_exec_transfer_proof(db: str, request: FixtureRequest) -> None:
    converter = MetamathConverter(request.getfixturevalue(db))
    assert converter

    extracted_axioms = []
    for axiom_name in converter.exported_axioms:
        axiom = converter.get_axiom_by_name(axiom_name)
        if isinstance(axiom, AxiomWithAntecedents):
            extracted_axioms.append(convert_to_implication(axiom.antecedents, axiom.pattern))
            continue
        extracted_axioms.append(axiom.pattern)

    extracted_claims = [converter.get_lemma_by_name(lemma_name).pattern for lemma_name in converter.lemmas]

    # TODO: Extract this code in transfer.py to a function
    class TranslatedProofSkeleton(ProofExp):
        def __init__(self) -> None:
            super().__init__(axioms=extracted_axioms, claims=extracted_claims)

        def execute_proofs_phase(self, interpreter: Interpreter) -> None:
            assert interpreter.phase == ExecutionPhase.Proof
            exec_proof(converter, 'goal', self, interpreter)

    proofexp = TranslatedProofSkeleton()
    interpreter = StatefulInterpreter(
        ExecutionPhase.Gamma,
        [Claim(claim) for claim in extracted_claims],
    )
    proofexp.execute_full(interpreter)

    assert interpreter.stack == [Proved(converter.get_lemma_by_name('goal').pattern)]
