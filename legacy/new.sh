#/bin/bash

mkdir $1
cd $1
getpdb $1
grep "REMARK 350" *.pdb
cd ..

