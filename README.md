# TLS migration to PQC hybrid standards

## 1. First time environment setup:

````
docker build -t pqc-env . 
docker run -it -v $(pwd):/opt/pqc_workspace --name pqc-lab pqc-env
````

#### With container running:

- Clone and compile liboqs and OpenSSL

````
./scripts/init_setup.sh
````

- Check OQS provider is active, and get KEM-algorithms in OpenSSL:

````
openssl list -providers -provider default -provider oqsprovider
openssl list -kem-algorithms -provider oqsprovider
`````
- Copy custom OpenSSL configuration file inside container to configure `oqsprovider`
````
cp /etc/ssl/openssl.cnf config/openssl_pqc.cnf
````
<br>

## 2. Connection

- Create RSA key and certificate:


````
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes -subj "/CN=TFG-PQC"
````

- Start server (OpenSSl s_server, not definitive):

````
openssl s_server -cert server.crt -key server.key -accept 4433 -www -tls1_3 -groups X25519MLKEM768
````

- Open two more terminals for the client and packet capture, and start a container on each one:

````
docker exec -it pqc-lab bash
````
On one terminal run:
````
tcpdump -i lo port 4433 -w captura_tfg.pcap
````
On the other create a connection with the server using hybrid encryption X25519MLKEM768 (We add the flag `-trace` for better handshake tracking)
```
openssl s_client -connect localhost:4433 -tls1_3 -groups X25519MLKEM768 -trace
````
<br>
Stop the container:

````
exit
`````
Restart container:
````
docker start -ai pqc-lab
````