.PHONY: all clean sym baseline

all: sym baseline

sym:
	./build-initrd.sh $${PWD}/.. fed36 sym

baseline:
	./build-initrd.sh $${PWD}/.. fed36 base

clean:
	rm -f *.cpio.gz

