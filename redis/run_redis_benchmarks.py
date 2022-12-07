#!/bin/python3
import os
import csv
import time

MAX_INSTANCES = 7
SERVER_NODE = '192.168.122.18'
tmp_results_path = 'tmp_redis_results.csv'
REDIS_BENCH_REQUESTS = 250000
EXPERIMENT_TYPE = 'different_nodes_vm'

IPC_SHORTCUT_LIB = './Symbi-OS/artifacts/ipc_interposer/ipc_shortcut.so'
IPC_SERVER_BIN = './Symbi-OS/artifacts/ipc_interposer/server'
REDIS_BIN = './Symbi-OS/artifacts/redis/fed36/redis-server'
REDIS_SERVER_ARGS = "--protected-mode no --save '' --appendonly no --port {} &> /dev/null"

SHOULD_USE_IPC = False

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
        f.write(f'{str(n)},{str(aggregate_throughput)},{EXPERIMENT_TYPE}\n')

############################################################################

if __name__ == '__main__':
    run_idx = 1
    for n in range(1, MAX_INSTANCES + 1, 1):
        print(f'[*] ----- Running {n} redis-server instances -----')
        #if run_idx < 3:
        if True:
            # For the first two runs, get a good number
            # of iterations in to generate error bars.
            for _ in range(0, 6):
                run_n_redis_benchmarks(n)
        else:
            run_n_redis_benchmarks(n)

        run_idx += 1
