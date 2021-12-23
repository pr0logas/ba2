
extern crate secp256k1;
extern crate crypto;
extern crate rand;
extern crate rust_base58;
extern crate bech32;

use secp256k1::Secp256k1;
use rand::rngs::OsRng;

mod address;
const ADDRESS_COUNT: u32  = 100001;

fn main(){

    let secp256k1 = Secp256k1::new();
    let mut rng = OsRng::new().expect("OsRng");
    
    for x in 1..ADDRESS_COUNT {
        let (_secret_key, public_key) = secp256k1.generate_keypair(&mut rng);
        let serialized_public_key = public_key.serialize();

        exec_args_p2pkh_p2wpkh(address::Network::Mainnet, &serialized_public_key, &_secret_key.to_string(), x);
    }
}


fn exec_args_p2pkh_p2wpkh(network: address::Network, serialized_public_key: &[u8], secret_key: &String, counter: u32) {
        let _address = address::BitcoinAddress::p2pkh(&serialized_public_key, network);
        println!("{0}, {1}, {2}", counter, _address.to_string(), secret_key);
}