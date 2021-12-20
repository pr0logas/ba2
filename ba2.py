import subprocess
import time
import sys
import os
import multiprocessing
import threading
from pymongo import MongoClient
from pymongo.errors import AutoReconnect

MONGO_HOST = 'mongodb://127.0.0.1:27017/'
FOUNDED_WALLETS_PATH='found_wallets.txt'
BIN_PATH = '/usr/bin/rust-bitcoin-address-generator'
DEFAULT_CPU_CORES = 1

def start_mongo():
    with MongoClient(MONGO_HOST) as client:
        db = client.btc
    return db

def write_to_file(path, wallet):
    with open(path, "a") as f:
        f.write(wallet)
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
    pot_sleep_time = 900
    db = start_mongo()
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

def start_generator(workernum):
    start_time = time.time()

    result = subprocess.check_output(BIN_PATH,shell=True).strip().splitlines()
    db = start_mongo()

    all_wallets_tmp = []

    for line in result:
        res = line.decode('utf-8').split(',')
        number = res[0].strip()
        address = res[1].strip()
        private_key = res[2].strip()
        all_wallets_tmp.append(address)

        write_query = {"wallet": address , "privkey" : private_key}
        mongo_write_generated_private_keys_with_wallets(db, write_query)

    query_result = mongo_send_find_query_many(db, all_wallets_tmp)

    if query_result != []:
        print(f"Wallet Found! Worker-{workernum} {query_result}")
        write_to_file(FOUNDED_WALLETS_PATH, 'Wallet Found!' + str(query_result) + '\n')


    print(f"--- Worker{workernum}--- {(time.time() - start_time)} seconds ---")
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