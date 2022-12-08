#!/bin/python3
import os
import csv
import time
import argparse
parser = argparse.ArgumentParser()

parser.add_argument("-n", "--name", help="Name of the run", required=True)
parser.add_argument("-s", "--server", help="IPv4 address of the server hosting redis instances", default="192.168.122.18")
parser.add_argument("-t", "--ipc_threads", help="Threads to be launched by the IPC server")
parser.add_argument("-m", "--mode", help="Specify 'ipc' in order to use IPC approach", default="normal")
parser.add_argument("-i", "--iterations", help="Number of iterations for each run", type=int, default=5)
parser.add_argument("-max_instances", "--max_instances", help="Maximium number of redis instances to scale to", type=int, default=7)

args = parser.parse_args()

MAX_INSTANCES = args.max_instances
SERVER_NODE = args.server
tmp_results_path = 'tmp_redis_results.csv'
REDIS_BENCH_REQUESTS = 500000
EXPERIMENT_NAME = args.name
ITERATIONS_PER_RUN = args.iterations
IPC_SERVER_THREADS = args.ipc_threads

IPC_SHORTCUT_LIB = './Symbi-OS/artifacts/ipc_interposer/ipc_shortcut.so'
IPC_SERVER_BIN = './Symbi-OS/artifacts/ipc_interposer/server'
REDIS_BIN = './Symbi-OS/artifacts/redis/fed36/redis-server'
REDIS_SERVER_ARGS = "--protected-mode no --save '' --appendonly no --port {} &> /dev/null"

SHOULD_USE_IPC = False
if args.mode == "ipc":
    SHOULD_USE_IPC = True

def print_experiment_header():
    print(f'########### {EXPERIMENT_NAME} ###########')
    print(f'\tServer Node         : {SERVER_NODE}')
    print(f'\tMax Redis Instances : {MAX_INSTANCES}')
    print(f'\tIterations Per Run  : {ITERATIONS_PER_RUN}')
    print(f'\tUsing IPC           : {SHOULD_USE_IPC}')
    print(f'\tIPC Server Threads  : {IPC_SERVER_THREADS}')

def run_server_cmd(cmd: str, daemon: bool, local_daemon: bool = False):
    if daemon:
        server_cmd = f'ssh {SERVER_NODE} "{cmd} &"'
    else:
        server_cmd = f'ssh {SERVER_NODE} "{cmd}"'

    if local_daemon:
        server_cmd += ' &'

    # Run the command over ssh inside the server node
    os.system(server_cmd)

def run_n_redis_benchmarks(n: int):
    port = 6379

    os.system(f'rm -rf {tmp_results_path}')

    if SHOULD_USE_IPC:
        # Starting the IPC server
        if IPC_SERVER_THREADS is not None:
            run_server_cmd(f'{IPC_SERVER_BIN} {IPC_SERVER_THREADS} &>/dev/null', True, True)
        else:
            run_server_cmd(f'{IPC_SERVER_BIN} {n} &>/dev/null', True, True)

        time.sleep(3)

    for i in range(0, n):
        port = 6379 + i
        
        if SHOULD_USE_IPC:
            run_server_cmd(f'LD_PRELOAD=\'{IPC_SHORTCUT_LIB}\' {REDIS_BIN} {REDIS_SERVER_ARGS.format(port)}', True)
        else:
            run_server_cmd(f'{REDIS_BIN} {REDIS_SERVER_ARGS.format(port)}', True)

        time.sleep(0.1)

    time.sleep(1)
    port = 6379

    for i in range(0, n - 1):
        os.system(f'redis-benchmark -h {SERVER_NODE} -t set -n {str(REDIS_BENCH_REQUESTS)} -p {str(port)} --csv >> {tmp_results_path} &')
        port += 1

    # Final redis benchmark should execute on the main thread
    os.system(f'redis-benchmark -h {SERVER_NODE} -t set -n {str(REDIS_BENCH_REQUESTS)} -p {str(port)} --csv >> {tmp_results_path}')

    time.sleep(3)

    run_server_cmd('bash -c \'pkill -9 redis-server\'', False)
    if SHOULD_USE_IPC:
        # Kill the IPC server
        if IPC_SERVER_THREADS is not None:
            run_server_cmd(f'{IPC_SERVER_BIN}_killer {IPC_SERVER_THREADS} &>/dev/null', False)
        else:
            run_server_cmd(f'{IPC_SERVER_BIN}_killer {n} &>/dev/null', False)
    
    time.sleep(1)

    # Parse the results
    aggregate_throughput = 0

    with open(tmp_results_path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        idx = 0
        for row in reader:
            idx += 1
            row_entry = row[0]
            entries = row_entry.split(',')
            value = entries[1].replace('"', '')
            print(f'Redis Instance: {str(idx)} TP: {value} rps')
            aggregate_throughput += round(float(value), 2)

    print(f'Redis Instances: {str(n)}')
    print(f'Throughput: {str(aggregate_throughput)} rps')

    if os.path.isfile('redis_results.csv') is not True:
        with open('redis_results.csv', 'w+') as f:
            f.write('"redis_instances","throughput","type"')
            f.write('\n')

    with open('redis_results.csv', 'a') as f:
        f.write(f'{str(n)},{str(aggregate_throughput)},{EXPERIMENT_NAME}\n')

############################################################################

if __name__ == '__main__':
    print_experiment_header()

    run_idx = 1
    for n in range(1, MAX_INSTANCES + 1, 1):
        print(f'[*] ----- Running {n} redis-server instances -----')
        for _ in range(0, ITERATIONS_PER_RUN):
            run_n_redis_benchmarks(n)

        run_idx += 1
