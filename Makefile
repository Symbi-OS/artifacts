# Phony target list
.PHONY: all clean

TOP_DIR=all_releases

all: $(TOP_DIR)/Tools $(TOP_DIR)/Symlib $(TOP_DIR)/Linux

# Make all_releases dir
$(TOP_DIR):
	mkdir $@

TOOLS_REL_PATH=https://api.github.com/repos/Symbi-OS/Tools/releases/latest
# Put all Tools releases TOP_DIR/Tools
$(TOP_DIR)/Tools: $(TOP_DIR)
	mkdir $@
	# Get all releases
	cd $@ && curl $(TOOLS_REL_PATH) | grep browser_download_url | cut -d '"' -f 4 | xargs wget 
	mkdir -p $@/bin/
	mv $@/cr_tool $@/bin/
	mv $@/idt_tool $@/bin/
	chmod +x $@/bin/{cr_tool,idt_tool}

	mkdir -p $@/bin/recipes/
	mv $@/interposing_mitigator.sh $@/bin/recipes/
	mv $@/mitigate_all.sh $@/bin/recipes/
	chmod +x $@/bin/recipes/{interposing_mitigator.sh,mitigate_all.sh}


	mkdir -p $@/shortcut
	mv $@/sc_lib.so $@/shortcut/
	mv $@/shortcut.sh $@/shortcut/
	chmod +x $@/shortcut/{sc_lib.so,shortcut.sh}


SYMLIB_REL_PATH=https://api.github.com/repos/Symbi-OS/Symlib/releases/latest
# Get all Symlib releases
$(TOP_DIR)/Symlib: $(TOP_DIR)
	mkdir $@
	# Get all releases
	cd $@ && curl $(SYMLIB_REL_PATH) | grep browser_download_url | cut -d '"' -f 4 | xargs wget
	chmod +x $(TOP_DIR)/Symlib/libSym.so 

LINUX_REL_PATH=https://api.github.com/repos/Symbi-OS/linux/releases/latest
# Get all Linux releases
$(TOP_DIR)/Linux: $(TOP_DIR)
	mkdir $@
	# Get all releases
	# NOTE: Skipping the (large) vmlinux file which is useful for debugging
	cd $@ && curl $(LINUX_REL_PATH) | grep browser_download_url | grep -v vmlinux | cut -d '"' -f 4 | xargs wget

update:
	make -C ../Tools/bin/ipc_shortcut clean
	make -C ../Tools/bin/ipc_shortcut
	cp ../Tools/bin/ipc_shortcut/ipc_shortcut.so ./ipc_interposer
	make -C ../LinuxPrototypes/shmem_ipc clean
	make -C ../LinuxPrototypes/shmem_ipc
	cp ../LinuxPrototypes/shmem_ipc/server ./ipc_interposer

clean:
	rm -rf all_releases *.rdb