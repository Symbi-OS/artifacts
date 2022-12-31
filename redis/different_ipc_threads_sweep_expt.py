#!/bin/python3
import os

REDIS_INSTANCES = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
IPC_THREAD_COUNTS = [1, 2, 4, 8, 16, 24, 32, 40, 64]

for redis_instance_count in REDIS_INSTANCES:
    # Running the control group (non-ipc approach)
    os.system(f'./run_redis_benchmarks.py -n non_ipc -s 192.168.122.66 --max_instances={redis_instance_count} --one_shot')

    for thread_count in IPC_THREAD_COUNTS:
        os.system(f'./run_redis_benchmarks.py -n ipc_{thread_count}_thread -s 192.168.122.66 --max_instances={redis_instance_count} --mode="ipc" --ipc_threads={thread_count} --one_shot')
