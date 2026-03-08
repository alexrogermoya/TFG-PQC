#!/bin/bash
git clone https://github.com/open-quantum-safe/liboqs.git
cd liboqs
mkdir build
cd build
cmake -GNinja -DBUILD_SHARED_LIBS=ON .. #La variable -DBUILD_SHARED_LIBS=ON permet que oqs-provider es pugui connectar
ninja
ninja install
cd ../..


git clone https://github.com/open-quantum-safe/oqs-provider.git
cd oqs-provider
mkdir build
cd build
cmake -GNinja ..
ninja
ninja install
cd ../..


ldconfig

