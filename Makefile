# Phony target list
.PHONY: all clean

all: update

update:
	make -C ../Tools/bin/ipc_shortcut clean
	make -C ../Tools/bin/ipc_shortcut
	cp ../Tools/bin/ipc_shortcut/ipc_shortcut.so ./ipc_interposer
	make -C ../LinuxPrototypes/shmem_ipc clean
	make -C ../LinuxPrototypes/shmem_ipc
	cp ../LinuxPrototypes/shmem_ipc/server ./ipc_interposer
	cp ../LinuxPrototypes/shmem_ipc/server_killer ./ipc_interposer

virt-ramdisk: $(TOP_DIR)/Tools $(TOP_DIR)/Symlib $(TOP_DIR)/Linux
	${MAKE} -C initrd

# Make all_releases dir
$(TOP_DIR):
	mkdir $@

run_redis1:
	./redis/fed36/redis-server --port 6379

run_redis2:
	./redis/fed36/redis-server --port 6380

run_ipc_redis1:
	LD_PRELOAD="ipc_interposer/ipc_shortcut.so" ./redis/fed36/redis-server --port 6379

run_ipc_redis2:
	LD_PRELOAD="ipc_interposer/ipc_shortcut.so" ./redis/fed36/redis-server --port 6380

run_benchmark1:
	redis-benchmark -t set -n 10000000 -c 100 -p 6379

run_benchmark2:
	redis-benchmark -t set -n 10000000 -c 100 -p 6380

run_server:
	./ipc_interposer/server $(THREADS)

run_kill:
	./ipc_interposer/server_killer 1

clean:
	rm -rf *.rdb
	rm -rf all_releases
	${MAKE} -C initrd clean
