.PHONY: all clean sym baseline

all: sym deep-sc baseline

sym:
	./build-initrd.sh $${PWD}/.. fed36 sym

deep-sc:
	./build-initrd.sh $${PWD}/.. fed36 deep-sc

baseline:
	./build-initrd.sh $${PWD}/.. fed36 base

clean:
	rm -f *.cpio.gz

