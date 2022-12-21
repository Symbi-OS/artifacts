#!/bin/bash
ITERATIONS_PER_RUN=20

./run_redis_benchmarks.py --name="n_redis" -i $ITERATIONS_PER_RUN

printf "\n"
sleep 1

./run_redis_benchmarks.py --name="n_redis_n_ipc_threads" -i $ITERATIONS_PER_RUN --mode="ipc"

printf "\n"
sleep 1

./run_redis_benchmarks.py --name="n_redis_1_ipc_thread" -i $ITERATIONS_PER_RUN --mode="ipc" --ipc_threads=1

printf "\n"
sleep 1

./run_redis_benchmarks.py --name="n_redis_2_ipc_threads" -i $ITERATIONS_PER_RUN --mode="ipc" --ipc_threads=2

printf "\n"
sleep 1

./run_redis_benchmarks.py --name="n_redis_3_ipc_threads" -i $ITERATIONS_PER_RUN --mode="ipc" --ipc_threads=3

printf "\n"
sleep 1

./run_redis_benchmarks.py --name="n_redis_4_ipc_threads" -i $ITERATIONS_PER_RUN --mode="ipc" --ipc_threads=4

printf "\n"
sleep 1
