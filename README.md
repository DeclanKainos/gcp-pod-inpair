# inpair
InPost data driven air quality visualisation across Poland

Possible thanks to InPost exposing their [API ShipX](https://dokumentacja-inpost.atlassian.net/wiki/spaces/PL/pages/622754/API+ShipX)


Designed to run as an AWS Lambda function.
The function stores results in an S3 bucket, which powers a static website. It is triggered hourly to refresh the data.

http://www.inpair.pl

http://inpair.s3-website-eu-west-1.amazonaws.com/


![preview](https://github.com/piotrgo/inpair/assets/4050128/9ee56dbb-4d8e-4840-a0c7-2acc9b2aff13)

## Running locally with Docker
Ensure that the relevant API key is specified in a .env file 
with the environment var for the API key set as shown below
```text
INPOST_API_TOKEN={YOUR_API_TOKEN}
S3_BUCKET_NAME={YOUR_S3_BUCKET_NAME}
```

If your local testing environment is behind a proxy (e.g. ZScaler),
add the following lines to import the required cacert.pem into
your docker container. this should be BEFORE the pip install step:

```dockerfile
# Copy your local CA cert into the container (if it exists)
COPY cacert.pem /tmp/cacert.pem

# Ensure Python/requests uses proper CA certs
ENV SSL_CERT_FILE="/tmp/cacert.pem"
ENV REQUESTS_CA_BUNDLE="/tmp/cacert.pem"

```

Docker commands:
```shell
docker build -t inpost-map-fn-lambda .
docker run --env-file .env -p 8080:8080 inpost-map-fn-lambda
```

To test the lambda function locally, run the line below and
analyse the log output and response payload:
```shell
curl -XPOST "http://localhost:8080/2015-03-31/functions/function/invocations" -d '{}'
```
