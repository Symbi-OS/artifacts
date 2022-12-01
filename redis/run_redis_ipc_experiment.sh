#!/bin/bash

EXPT_RESULTS_FILE='redis_ipc_expt_results.csv'
RUN_COUNT=1

REDIS_SERVER_PATH='fed36/redis-server'
IPC_INTERPOSER_DIR='../ipc_interposer'

IPC_INTERPOSER_LIB="$IPC_INTERPOSER_DIR/ipc_shortcut.so"
IPC_SERVER="$IPC_INTERPOSER_DIR/server"
IPC_SERVER_KILLER="$IPC_INTERPOSER_DIR/server_killer"

IPC_SERVER_CORE=0
IPC_SERVER_THREADS=1

REDIS_BENCHMARK_CORES=6,7
REDIS_BENCHMARK_CLIENTS=100

function kill_ipc_server {
	./$IPC_SERVER_KILLER 1
}

function run_redis {
	./$REDIS_SERVER_PATH
}

function run_redis_with_ipc {
	LD_PRELOAD="$IPC_INTERPOSER_LIB" ./$REDIS_SERVER_PATH
}

function run_redis_benchmark {
	taskset -c $REDIS_BENCHMARK_CORES redis-benchmark --csv -q -n 10000000 -c $REDIS_BENCHMARK_CLIENTS -d 3 -k 1 -t get,set -P 14
}

############################################################################################################
############################################################################################################

function run_redis_ipc_test {
	run_redis_with_ipc &> /dev/null &
	sleep 1
	run_redis_benchmark |& tee -a  $EXPT_RESULTS_FILE
	redis-cli shutdown
	kill_ipc_server &> /dev/null
}

rm -rf $EXPT_RESULTS_FILE

printf "System Information\n"
printf "\tKernel: $(uname -r)\n"
printf "\n"

i=0
while [ $i -lt $RUN_COUNT ]; do
	echo "<----- Vanilla Redis ----->"
	run_redis &> /dev/null &
	sleep 1
	run_redis_benchmark |& tee -a  $EXPT_RESULTS_FILE
	redis-cli shutdown
	wait
	echo "<------------------------->"
	sleep 1

	printf "\n\n"

	echo "*----- Redis + Linux IPC -----*"
	taskset -c $IPC_SERVER_CORE ./$IPC_SERVER $IPC_SERVER_THREADS &> /dev/null &
	run_redis_ipc_test
	wait
	echo "*-----------------------------*"
	sleep 1
	printf "\n\n"

	i=$((i + 1))
	printf "COMPLETED RUNS: $i/$RUN_COUNT\n\n"
done

wait
printf "\n"
echo "Experiment Completed!"

