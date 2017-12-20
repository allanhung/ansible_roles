cfssl gencert -initca ../root-csr.json | cfssljson --bare root-ca
cfssl gencert -ca root-ca.pem -ca-key root-ca-key.pem -config ../etcd-sign.json -hostname 127.0.0.1,localhost,10.42.231.101,10.42.231.102,10.42.231.103 ../etcd-csr.json | cfssljson --bare etcd
