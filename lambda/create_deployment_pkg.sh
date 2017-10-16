#! /usr/bin/sh

# This script is for building a Numpy/Pandas ready deployment package for AWS Lambda
# Adapted from https://github.com/vitolimandibhrata/aws-lambda-numpy

# Run on an AWS EC2 with >2GB memory (t2.small or larger), necessary to build numpy
# Be sure to have lambda_function.py ready

LAMBDA_FUNCTION="lambda_function.py"
NUMPY_VERSION='v1.13.1'
NUMPY_DEPENDENCY_LIBRARIES=(
	libatlas.so.3
	libf77blas.so.3
	libptcblas.so.3
	libcblas.so.3
	libgfortran.so.3
	libptf77blas.so.3
	libclapack.so.3
	liblapack.so.3
	libquadmath.so.0
)

## Prepare environment

# Install python development packages for building numpy
sudo yum -y install python-devel
sudo yum -y install gcc-c++
sudo yum -y install gcc-gfortran
sudo yum -y install libgfortran

# Install Numpy dependencies
sudo yum -y install blas
sudo yum -y install lapack
sudo yum -y install atlas-sse3-devel

# Extract only the necessary SO files
sudo mkdir -p /var/task/lib
sudo cp /usr/lib64/libgfortran.so.3 /var/task/lib/
sudo cp /usr/lib64/libquadmath.so.0 /var/task/lib/
sudo cp /usr/lib64/atlas-sse3/*.so.3 /var/task/lib/

# Create virtual environment where we will build numpy
virtualenv lambda
source lambda/bin/activate

## Get numpy/pandas

# Install Cython for building numpy
sudo lambda/bin/pip install Cython

# Retrieve Numpy src
sudo yum -y install git
git clone https://github.com/numpy/numpy.git lambda/numpy
pushd lambda/numpy

# Choose the numpy version we want
git checkout $NUMPY_VERSION

# Ensure numpy finds the native libraries we will include in deploy.zip
cat > site.cfg <<EOF
[atlas]
libraries = lapack, f77blas, cblas, atlas
search_static_first = true
runtime_library_dirs = /var/task/lib
extra_link_args = -lgfortran -lquadmath
EOF

# Install numpy
python setup.py build
python setup.py install
popd

# Install pandas with new numpy
sudo /lambda/lib/pip install pandas

## Construct deployment package zip

mkdir deploy

# Include python modules
cp -r lambda/lib/python2.7/site-packages/* deploy/ 

# Remove fluff
rm -r deploy/easy_install*
rm -r deploy/_markerlib*
rm -r deploy/pip*
rm -r deploy/pkg_resources
rm -r setuptools*

# Include python native modules numpy/pandas
cp -r lambda/lib64/python2.7/site-packages/numpy*.egg/numpy deploy/
cp -r lambda/lib64/python2.7/site-packages/pandas deploy/

# Include statically linked libraries
cp -r /var/task/lib deploy/lib

# Include your lambda function
cp $LAMBDA_FUNCTION deploy/

# zip into deploy.zip
# deploy.zip is ~47MB zipped and must be uploaded to S3 bucket to be utilized by lambda
# AWS Lambda maximum zipped deployment package size is 50MB so be careful adding packages
pushd deploy
zip -r ../deploy *
popd
