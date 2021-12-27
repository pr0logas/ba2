import subprocess
import time
import sys
import os
import json
import multiprocessing
import threading
from pymongo import MongoClient
from pymongo.errors import AutoReconnect

MONGO_HOST = 'mongodb://127.0.0.1:27017/'
FOUNDED_WALLETS_PATH='found_wallets.txt'
BIN_PATH = '/usr/bin/rust-bitcoin-address-generator'
DEFAULT_CPU_CORES = 1

SPECIFIC_PREFIXES_INT = [
    '11111',
    '12222',
    '13333',
    '14444',
    '15555',
    '16666',
    '17777',
    '18888',
    '19999'
]

SPECIFIC_PREFIXES_UPPER_STRING = [
    '1AAAA',
    '1BBBB',
    '1CCCC',
    '1DDDD',
    '1EEEE',
    '1FFFF',
    '1GGGG',
    '1HHHH',
    '1JJJJ',
    '1KKKK',
    '1LLLL',
    '1MMMM',
    '1NNNN',
    '1PPPP',
    '1QQQQ',
    '1RRRR',
    '1SSSS',
    '1TTTT',
    '1UUUU',
    '1VVVV',
    '1WWWW',
    '1XXXX',
    '1YYYY',
    '1ZZZZ'
]

SPECIFIC_PREFIXES_LOWER_STRING = [
    '1aaaa',
    '1bbbb',
    '1cccc',
    '1dddd',
    '1eeee',
    '1ffff',
    '1gggg',
    '1hhhh',
    '1iiii',
    '1jjjj',
    '1kkkk',
    '1mmmm',
    '1nnnn',
    '1pppp',
    '1qqqq',
    '1rrrr',
    '1ssss',
    '1tttt',
    '1uuuu',
    '1vvvv',
    '1wwww',
    '1xxxx',
    '1yyyy',
    '1zzzz'
]

SPECIFIC_END_INT = [
    '1111',
    '2222',
    '3333',
    '4444',
    '5555',
    '6666',
    '7777',
    '8888',
    '9999'
]

SPECIFIC_END_UPPER_STRING = [
    'AAAA',
    'BBBB',
    'CCCC',
    'DDDD',
    'EEEE',
    'FFFF',
    'GGGG',
    'HHHH',
    'JJJJ',
    'KKKK',
    'LLLL',
    'MMMM',
    'NNNN',
    'PPPP',
    'QQQQ',
    'RRRR',
    'SSSS',
    'TTTT',
    'UUUU',
    'VVVV',
    'WWWW',
    'XXXX',
    'YYYY',
    'ZZZZ'
]

SPECIFIC_END_LOWER_STRING = [
    'aaaa',
    'bbbb',
    'cccc',
    'dddd',
    'eeee',
    'ffff',
    'gggg',
    'hhhh',
    'iiii',
    'jjjj',
    'kkkk',
    'mmmm',
    'nnnn',
    'pppp',
    'qqqq',
    'rrrr',
    'ssss',
    'tttt',
    'uuuu',
    'vvvv',
    'wwww',
    'xxxx',
    'yyyy',
    'zzzz'
]

CUSTOM_SEARCH = [
    '123456789',
    '198765432',
    '1ABCDEF',
    '1abcdef',
    'ABCDEF',
    'abcdef',
]

def start_mongo():
    with MongoClient(MONGO_HOST) as client:
        db = client.btc
    return db

def write_to_file(path, wallet, priv):
    with open(path, "a") as f:
        f.write(wallet)
        f.write(priv)
        f.close()

def autoreconnect_retry(fn, retries=20):
    def db_op_wrapper(*args, **kwargs):
        tries = 0

        while tries < retries:
            try:
                return fn(*args, **kwargs)

            except AutoReconnect:
                tries += 1

        raise Exception("MongoDB not responding. No luck even after %d retries" % retries)

    return db_op_wrapper


@autoreconnect_retry
def mongo_send_find_query_many(connection, arrayitems):
    return list(connection.wallets_with_balance.find({'wallet': {"$in": arrayitems}}, {"_id": 0}))

@autoreconnect_retry
def mongo_send_find_query(connection, query):
    return list(connection.wallets_with_balance.find(query, {"_id": 0, "wallet": 1}))

@autoreconnect_retry
def mongo_write_generated_private_keys_with_wallets_many(connection, arrayitems):
    return connection.generated_wallets_with_priv_keys.insert_many(arrayitems)

@autoreconnect_retry
def mongo_write_generated_private_keys_with_wallets(connection, write_query):
    return connection.generated_wallets_with_priv_keys.insert_one(write_query)

def check_if_user_arguments_not_empty():
    try:
        if len(sys.argv[1]) > 0:
            return True
    except IndexError:
        return False


def check_progress():
    time.sleep(10)
    pot_sleep_time = 120

    with MongoClient(MONGO_HOST) as client:
        db = client.btc

        while True:
            try:
                total_wallets = db['generated_wallets_with_priv_keys'].estimated_document_count()
                formated_number = f"{total_wallets:,}"
                print(f"/// Total number of wallets in DB: {formated_number} ///")
                stat = os.stat(FOUNDED_WALLETS_PATH)
                pot_sleep_time = 5
                print("")
                print(f"************************** HONEY POT! ************************************")
                print(f"*********** Please check the file: {FOUNDED_WALLETS_PATH} ***************")
                print("")

            except FileNotFoundError:
                pot_sleep_time = 900
                print(f"*** Found nothing so far ***")
                print(f"*** There are only: 1461501637330902918203684832716283019655932542976"
                      f" possible BTC addresses :) ***")


            except Exception as e:
                print(f"<IOwork> Something went wrong. Cannot get {FOUNDED_WALLETS_PATH} modification time!")
                print(e)
                pass
            time.sleep(pot_sleep_time)
        client.close()

def define_timer():
    return time.time()


def start_generator(workernum):
    global_start_time = define_timer()

    wallets_creation_time = define_timer()
    result = subprocess.check_output(BIN_PATH,shell=True).strip().splitlines()
    print(f"--- Worker{workernum} --- wallets creation took: {round((time.time() - wallets_creation_time), 2)} seconds ---")

    with MongoClient(MONGO_HOST) as client:
        db = client.btc

        all_wallets_tmp = []
        all_wallets_with_priv = []
        all_wallets_with_priv_tmp = {}

        aggregation_time = define_timer()
        for line in result:
            res = line.decode('utf-8').split(',')
            number = res[0].strip()
            address = res[1].strip()
            private_key = res[2].strip()
            privkey_decimal = str(int(private_key, 16))

            insertion_format_for_mongo = {"wallet" : address, "privkey" : private_key, "privkey_decimal" : privkey_decimal }

            all_wallets_tmp.append(address)
            all_wallets_with_priv_tmp[address] = private_key

            if address.startswith(tuple(SPECIFIC_PREFIXES_INT)) \
            or address.startswith(tuple(SPECIFIC_PREFIXES_UPPER_STRING)) \
            or address.startswith(tuple(SPECIFIC_PREFIXES_LOWER_STRING)) \
            or address.startswith(tuple(CUSTOM_SEARCH)) \
            or address.endswith(tuple(CUSTOM_SEARCH)) \
            or address.endswith(tuple(SPECIFIC_END_INT)) \
            or address.endswith(tuple(SPECIFIC_END_UPPER_STRING)) \
            or address.endswith(tuple(SPECIFIC_END_LOWER_STRING)):
                print(address)
                all_wallets_with_priv.append(insertion_format_for_mongo)

        wallets_count = len(all_wallets_tmp)
        formated_wallets_number = f"{wallets_count:,}"
        wallets_to_be_imported_count = len(all_wallets_with_priv)
        print(f"--- Worker{workernum} --- aggregations took: {round((time.time() - aggregation_time), 2)} seconds ---")

        wallets_insertion_time = define_timer()

        if wallets_to_be_imported_count > 0:
            mongo_write_generated_private_keys_with_wallets_many(db, all_wallets_with_priv)

        print(f"--- Worker{workernum} --- db inserts took: {round((time.time() - wallets_insertion_time), 2)} seconds ---")

        search_time = define_timer()
        query_result = mongo_send_find_query_many(db, all_wallets_tmp)
        print(f"--- Worker{workernum} --- db search took: {round((time.time() - search_time), 2)} seconds ---")

        if query_result != []:
            print(f"Wallet Found! Worker-{workernum} {query_result} {all_wallets_with_priv_tmp}")
            write_to_file(FOUNDED_WALLETS_PATH, 'Wallet Found!' + str(query_result) + '\n', json.dumps(all_wallets_with_priv_tmp))

        print(f"--- Worker{workernum} --- ALL processes took: ***{round((time.time() - global_start_time), 2)}*** seconds ({formated_wallets_number}/{wallets_to_be_imported_count} wallets) ---")
        
    client.close()
    start_generator(workernum)
        


def start_workers():
    if check_if_user_arguments_not_empty():
        print(f"Generating with {int(sys.argv[1])} CPU cores")
        for i in range(int(sys.argv[1])):
            p = multiprocessing.Process(target=start_generator, args=(i,))
            p.start()
    else:
        print(f"Generating with {DEFAULT_CPU_CORES} CPU cores")
        p = multiprocessing.Process(target=start_generator, args=(DEFAULT_CPU_CORES,))
        p.start()

start_workers()
threading.Thread(target=check_progress).start()