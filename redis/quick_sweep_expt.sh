#!/bin/bash

./run_redis_benchmarks.py -n non_ipc -s 192.168.122.66 --max_instances=40

printf "\n\n"
sleep 5

./run_redis_benchmarks.py -n ipc_1_thread -s 192.168.122.66 --max_instances=40 --mode="ipc" --ipc_threads=1

