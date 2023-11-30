use core::array::ArrayTrait;
fn load_transfer_example() -> (Array::<u8>, Array::<u8>, Array::<u8>) {
    let gamma = ArrayTrait::<u8>::new();
    let claims = ArrayTrait::<u8>::new();
    let proofs = ArrayTrait::<u8>::new();
    (gamma, claims, proofs)
}

fn load_transfer_batch_example() -> (Array::<u8>, Array::<u8>, Array::<u8>) {
    let mut gamma = ArrayTrait::<u8>::new();
    gamma.append(0xff);
    let claims = ArrayTrait::<u8>::new();
    let proofs = ArrayTrait::<u8>::new();
    (gamma, claims, proofs)
}

fn load_svm5_example() -> (Array::<u8>, Array::<u8>, Array::<u8>) {
    let gamma = ArrayTrait::<u8>::new();
    let claims = ArrayTrait::<u8>::new();
    let proofs = ArrayTrait::<u8>::new();
    (gamma, claims, proofs)
}

fn load_perceptron_example() -> (Array::<u8>, Array::<u8>, Array::<u8>) {
    let gamma = ArrayTrait::<u8>::new();
    let claims = ArrayTrait::<u8>::new();
    let proofs = ArrayTrait::<u8>::new();
    (gamma, claims, proofs)
}

#[derive(Drop)]
enum Input {
    Transfer,
    TransferBatch,
    SVM5,
    Perceptron,
}

fn load_input(example: Input) -> (Array::<u8>, Array::<u8>, Array::<u8>) {
    match example {
        Input::Transfer => load_transfer_example(),
        Input::TransferBatch => load_transfer_batch_example(),
        Input::SVM5 => load_svm5_example(),
        Input::Perceptron => load_perceptron_example(),
    }
}

// Unit tests module
#[cfg(test)]
mod tests {
    use core::array::ArrayTrait;
    use super::load_input;
    use super::Input;

    #[test]
    #[available_gas(100000)]
    fn test_match() {
        let (g, c, p) = load_input(Input::TransferBatch);

        assert(g.len() == 1, 'Hmm.. load_input failed!');
    }
}

