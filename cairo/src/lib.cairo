use debug::PrintTrait;

use inputs::load_input;
use inputs::Input;
use verifier::verify;

mod inputs;
mod verifier;

// Main
fn main() {
    'Reading proofs ... '.print();
    let (gamma, claims, proofs) = load_input(Input::Transfer);
    'Checking proofs ... '.print();
    verify(gamma, claims, proofs);
}

