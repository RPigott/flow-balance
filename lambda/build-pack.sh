#!/bin/sh

# Upgrade and install software
sudo yum -y update
sudo yum -y upgrade
sudo yum install -y \
    wget \
    gcc \
    gcc-c++ \
    python27-devel \
    python27-virtualenv \
    python27-pip \
    findutils \
    zlib-devel \
    zip \
    git

# Allow git
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true

# Make dummy virtualenv
rm -rf env
virtualenv env
source env/bin/activate

# Package fluff
pip install --upgrade pip wheel
pip install git+https://git-codecommit.us-west-2.amazonaws.com/v1/repos/ams-core

# Fresh packaging area
rm -rf pack
mkdir pack

# Include what is necessary
cp -r env/lib/python2.7/site-packages/* pack/
cp -r env/lib64/python2.7/site-packages/* pack/

# Remove what is not
find pack/ -type d -name 'tests' -exec rm -rf {} +
find pack/ -name '*.so' | xargs strip
find pack/ -name '*.so*' | xargs strip
find pack/ -name '*.pyc' --delete

rm -rf pack/pip*
rm -rf pack/wheel*
rm -rf pack/boto*
rm pack/easy_install.py

# Include the handler
pushd "$1"
cp -r * ../pack/
popd

# Pack it up
pushd pack
zip -FS -r9 ../pack.zip *
popd
deactivate
