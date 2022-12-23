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
parser.add_argument("-s", "--server", help="IPv4 address of the server hosting redis instances", default="192.168.122.18", required=True)
parser.add_argument("-t", "--ipc_threads", help="Threads to be launched by the IPC server")
parser.add_argument("-v", "--verbose", help="Verbose printing mode", action="store_true")

args = parser.parse_args()

TMP_RESULTS_PATH = 'tmp_redis_results.csv'
REDIS_START_PORT = 6379

IPC_SHORTCUT_LIB = './Symbi-OS/artifacts/ipc_interposer/ipc_shortcut.so'
IPC_SERVER_BIN = './Symbi-OS/artifacts/ipc_interposer/server'
REDIS_BIN = './Symbi-OS/artifacts/redis/fed36/redis-server'
REDIS_SERVER_ARGS = "--protected-mode no --save '' --appendonly no --port {} &> /dev/null"

SHOULD_USE_IPC = False
if args.mode == "ipc":
    SHOULD_USE_IPC = True

def print_experiment_header():
    print(f'########### {args.name} ###########')
    print(f'\tServer Node         : {args.server}')
    print(f'\tMax Redis Instances : {args.max_instances}')
    print(f'\tIterations Per Run  : {args.iterations}')
    print(f'\tUsing IPC           : {SHOULD_USE_IPC}')
    print(f'\tIPC Server Threads  : {args.ipc_threads}')

def kickoff_remote_servers(n: int):
    server_cmd_prefix = ''
    server_cmd_suffix = ''

    if SHOULD_USE_IPC:
        server_cmd_prefix = f'ssh {args.server} "LD_PRELOAD=\'{IPC_SHORTCUT_LIB}\' {REDIS_BIN} --protected-mode no --save '' --appendonly no --port'
        server_cmd_suffix = '&> /dev/null &"'
    else:
        server_cmd_prefix = f'ssh {args.server} "{REDIS_BIN} --protected-mode no --save '' --appendonly no --port'
        server_cmd_suffix = '&> /dev/null &"'

    # print the command about to run
    if args.verbose:
        [print(server_cmd_prefix + ' ' + str(port) + ' ' + server_cmd_suffix) for port in range(REDIS_START_PORT, REDIS_START_PORT + n)]

    # Note, if this causes failures, such as kex_exchange_identification: read: Connection reset by peer Connection reset by 192.168.1.2 port 22
    # Go into /etc/ssh/sshd_config and change MaxStartups and MaxSessions to a larger number like 512
    ps = [subprocess.Popen(server_cmd_prefix + ' ' + str(port) + ' ' + server_cmd_suffix, shell=True) for port in range(REDIS_START_PORT, REDIS_START_PORT + n)]

    [p.wait() for p in ps]

def kickoff_benchmarks(n):
    # Start all the benchmark processes, one for each redis instance, vary the ports.
    prefix = (f'redis-benchmark -h {args.server} -t set -n {str(args.requests)} -p')
    suffix = (f'--csv >> {TMP_RESULTS_PATH}')

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

    os.system(f'rm -rf {TMP_RESULTS_PATH}')

    if SHOULD_USE_IPC:
        # Starting the IPC server
        # For some reason the ssh call hangs even if the server
        # command is in the background, hence the second &.
        if args.ipc_threads is not None:
            server_cmd = f'ssh {args.server} "{IPC_SERVER_BIN} {args.ipc_threads} &>/dev/null &" &'
            if args.verbose:
                print(server_cmd)
        else:
            server_cmd = f'ssh {args.server} "{IPC_SERVER_BIN} {n} &>/dev/null &" &'
            if args.verbose:
                print(server_cmd)

        p = subprocess.Popen(server_cmd, shell=True) 
        p.wait()

        # The following sleep is necessary to ensure that the IPC server gets
        # setup and initialized properly, i.e. creates the shared memory backing file.
        time.sleep(3)

    kickoff_remote_servers(n)

    # This specific sleep is needed to ensure that all Redis servers are
    # properly setup, initialized, and ready to accept connections, which
    # happens after a maxmimum of a few hundred miliseconds after the launch.
    time.sleep(1)

    kickoff_benchmarks(n)

    kill_server_cmd = f'ssh {args.server} "bash -c \'pkill redis-server\'"'
    p = subprocess.Popen(kill_server_cmd, shell=True) 
    p.wait()

    if SHOULD_USE_IPC:
        server_cmd = ''

        # Kill the IPC server
        if args.ipc_threads is not None:
            server_cmd = f'ssh {args.server} "{IPC_SERVER_BIN}_killer {args.ipc_threads} &>/dev/null"'
        else:
            server_cmd = f'ssh {args.server} "{IPC_SERVER_BIN}_killer {n} &>/dev/null"'
    
        if args.verbose:
            print(server_cmd)

        p = subprocess.Popen(server_cmd, shell=True) 
        p.wait()

    time.sleep(1)

    # Parse the results
    aggregate_throughput = 0

    with open(TMP_RESULTS_PATH, newline='') as csvfile:
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
        f.write(f'{str(n)},{str(round(aggregate_throughput, 2))},{args.name}\n')

############################################################################

if __name__ == '__main__':
    print_experiment_header()


    # Instead of looping from 1 to MAX_INSTANCES, we can run a single experiment
    if args.one_shot:
        print(f'[*] ----- Running {args.max_instances} redis-server instances -----')
        # Run the experiment ITERATIONS_PER_RUN times
        for _ in range(0, args.iterations):
            run_n_redis_benchmarks(args.max_instances)
        exit(0)
    

    run_idx = 1
    for n in range(1, args.max_instances + 1, 1):
        print(f'[*] ----- Running {n} redis-server instances -----')
        for _ in range(0, args.iterations):
            run_n_redis_benchmarks(n)

        run_idx += 1
