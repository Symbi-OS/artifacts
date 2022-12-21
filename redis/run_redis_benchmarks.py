#!/bin/python3
import os
import csv
import time
import argparse
import subprocess
parser = argparse.ArgumentParser()

parser.add_argument("-i", "--iterations", help="Number of iterations for each run", type=int, default=5)
parser.add_argument("-m", "--mode", help="Specify 'ipc' in order to use IPC approach", default="normal")
parser.add_argument("-max_instances", "--max_instances", help="Maximium number of redis instances to scale to", type=int, default=7)
parser.add_argument("-n", "--name", help="Name of the run", required=True)
parser.add_argument("-o", "--one_shot", help="Run the max instances configuration only", action="store_true")
parser.add_argument("-r", "--requests", help="Number of requests to be sent to each redis instance", type=int, default=500000)
parser.add_argument("-s", "--server", help="IPv4 address of the server hosting redis instances", default="192.168.122.18")
parser.add_argument("-t", "--ipc_threads", help="Threads to be launched by the IPC server")
parser.add_argument("-v", "--verbose", help="Verbose printing mode", action="store_true")

args = parser.parse_args()

MAX_INSTANCES = args.max_instances
SERVER_NODE = args.server
tmp_results_path = 'tmp_redis_results.csv'
REDIS_BENCH_REQUESTS = args.requests
EXPERIMENT_NAME = args.name
ITERATIONS_PER_RUN = args.iterations
IPC_SERVER_THREADS = args.ipc_threads

REDIS_START_PORT = 6379

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
    # if verbose, print the command
    if args.verbose:
        print(server_cmd)
    # execute the command and exit if it fails. Print the command if it fails
    ret = os.system(server_cmd)
    if ret != 0:
        print(f'Failed to execute command: {server_cmd}, return value was {ret}' )
        exit(1)

def kickoff_remote_servers(n: int):
    if SHOULD_USE_IPC:
        [ run_server_cmd(f'LD_PRELOAD=\'{IPC_SHORTCUT_LIB}\' {REDIS_BIN} {REDIS_SERVER_ARGS.format(port)}', True)for port in range(REDIS_START_PORT, REDIS_START_PORT + n) ] 
    else:
        # TDOD: clean up for general case
        server_cmd_prefix = 'ssh 192.168.1.2 "./Symbi-OS/artifacts/redis/fed36/redis-server --protected-mode no --save '' --appendonly no --port'
        server_cmd_suffix = '&> /dev/null &"'
        # print the command about to run
        if args.verbose:
            [print(server_cmd_prefix + ' ' + str(port) + ' ' + server_cmd_suffix) for port in range(REDIS_START_PORT, REDIS_START_PORT + n)]

        # Note, if this causes failures, such as kex_exchange_identification: read: Connection reset by peer Connection reset by 192.168.1.2 port 22
        # Go into /etc/ssh/sshd_config and change MaxStartups and MaxSessions to a larger number like 512
        ps = [subprocess.Popen(server_cmd_prefix + ' ' + str(port) + ' ' + server_cmd_suffix, shell=True) for port in range(REDIS_START_PORT, REDIS_START_PORT + n)]

        [p.wait() for p in ps]

#        [ run_server_cmd(f'{REDIS_BIN} {REDIS_SERVER_ARGS.format(port)}', True) for port in range(REDIS_START_PORT, REDIS_START_PORT + n)]

def kickoff_benchmarks(n):
    # Start all the benchmark processes, one for each redis instance, vary the ports.
    prefix = (f'redis-benchmark -h {SERVER_NODE} -t set -n {str(REDIS_BENCH_REQUESTS)} -p')
    suffix = (f'--csv >> {tmp_results_path}')

    # if verbose, print the command
    if args.verbose:
        [print(prefix + ' ' + str(port) + ' ' + suffix) for port in range(REDIS_START_PORT, REDIS_START_PORT + n)]

    # start all processes in the background and wait on them
    if args.verbose:
        print('\033[91mStarting benchmarks\033[0m')

    # start a timer
    start_time = time.time()

    ps = [subprocess.Popen( prefix + ' ' + str(port) + ' ' + suffix, shell=True) for port in range(REDIS_START_PORT, REDIS_START_PORT + n)]

    # wait on all processes to finish
    [p.wait() for p in ps]
    end_time = time.time()

    if args.verbose:
        print('\033[92mFinished benchmarks\033[0m')

    # Print time taken, rounded to 2 decimal places
    print(f'\033[92mTime taken: {round(end_time - start_time, 2)} seconds\033[0m')

def run_n_redis_benchmarks(n: int):

    os.system(f'rm -rf {tmp_results_path}')

    if SHOULD_USE_IPC:
        # Starting the IPC server
        if IPC_SERVER_THREADS is not None:
            run_server_cmd(f'{IPC_SERVER_BIN} {IPC_SERVER_THREADS} &>/dev/null', True, True)
        else:
            run_server_cmd(f'{IPC_SERVER_BIN} {n} &>/dev/null', True, True)

        time.sleep(3)

    kickoff_remote_servers(n)

    time.sleep(1)

    kickoff_benchmarks(n)

    run_server_cmd('bash -c \'pkill redis-server\'', False)
    if SHOULD_USE_IPC:
        # Kill the IPC server
        if IPC_SERVER_THREADS is not None:
            if args.verbose:
                print(f'{IPC_SERVER_BIN}_killer {IPC_SERVER_THREADS} &>/dev/null')
            run_server_cmd(f'{IPC_SERVER_BIN}_killer {IPC_SERVER_THREADS} &>/dev/null', False)
        else:
            if args.verbose:
                print(f'{IPC_SERVER_BIN}_killer {n} &>/dev/null')
            run_server_cmd(f'{IPC_SERVER_BIN}_killer {n} &>/dev/null', False)
    
    time.sleep(1)

    # Parse the results
    aggregate_throughput = 0

    with open(tmp_results_path, newline='') as csvfile:
        # Read the second line of the csv file and add the throughput to the aggregate throughput
        # the throughput is the second column of the csv file, on even number lines
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for i, row in enumerate(reader):
            if i % 2 == 1:
                # remove double quotes from the throughput
                aggregate_throughput += round(float(row[1].replace('"', '')), 2)


    print(f'Redis Instances: {str(n)}')
    print(f'Throughput: {str(round(float(aggregate_throughput) , 2))} rps')
    print(f'Throughput k: {str(round(float(aggregate_throughput/1000), 2))} k-rps')

    if os.path.isfile('redis_results.csv') is not True:
        with open('redis_results.csv', 'w+') as f:
            f.write('"redis_instances","throughput","type"')
            f.write('\n')

    with open('redis_results.csv', 'a') as f:
        f.write(f'{str(n)},{str(aggregate_throughput)},{EXPERIMENT_NAME}\n')

############################################################################

if __name__ == '__main__':
    print_experiment_header()


    # Instead of looping from 1 to MAX_INSTANCES, we can run a single experiment
    if args.one_shot:
        print(f'[*] ----- Running {MAX_INSTANCES} redis-server instances -----')
        # Run the experiment ITERATIONS_PER_RUN times
        for _ in range(0, ITERATIONS_PER_RUN):
            run_n_redis_benchmarks(MAX_INSTANCES)
        exit(0)
    

    run_idx = 1
    for n in range(1, MAX_INSTANCES + 1, 1):
        print(f'[*] ----- Running {n} redis-server instances -----')
        for _ in range(0, ITERATIONS_PER_RUN):
            run_n_redis_benchmarks(n)

        run_idx += 1
