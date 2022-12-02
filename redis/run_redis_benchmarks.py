#!/bin/python3
import os
import csv
import time

MAX_INSTANCES = 32
SERVER_NODE = '192.168.19.66'
tmp_results_path = 'tmp_redis_results.csv'
REDIS_BENCH_REQUESTS = 500000

def run_n_redis_benchmarks(n: int):
    port = 6379

    os.system(f'rm -rf {tmp_results_path}')

    for i in range(0, n):
        port = 6379 + i
        os.system(f'ssh {SERVER_NODE} "redis-server --port {str(port)} --protected-mode no --save \'\' --appendonly no &> /dev/null &"')

    time.sleep(1)
    port = 6379

    for i in range(0, n - 1):
        os.system(f'redis-benchmark -h {SERVER_NODE} -t set -n {str(REDIS_BENCH_REQUESTS)} -p {str(port)} --csv >> {tmp_results_path} &')
        port += 1

    # Final redis benchmark should execute on the main thread
    os.system(f'redis-benchmark -h {SERVER_NODE} -t set -n {str(REDIS_BENCH_REQUESTS)} -p {str(port)} --csv >> {tmp_results_path}')

    time.sleep(6)

    os.system(f'ssh {SERVER_NODE} "bash -c \'pkill -9 redis-server\'"')

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
            f.write('"redis_instances","throughput"')
            f.write('\n')

    with open('redis_results.csv', 'a') as f:
        f.write(f'{str(n)},{str(aggregate_throughput)}\n')

############################################################################

if __name__ == '__main__':
    os.system('rm -rf redis_results.csv')

    for n in range(1, MAX_INSTANCES + 1, 4):
        print(f'[*] ----- Running {n} redis-server instances -----')
        run_n_redis_benchmarks(n)
