# inpair
InPost data driven air quality visualisation across Poland

Possible thanks to InPost exposing their [API ShipX](https://dokumentacja-inpost.atlassian.net/wiki/spaces/PL/pages/622754/API+ShipX)


Designed to run as either an AWS Lambda function or a Google Cloud Run service.
The AWS Lambda variant stores results in an S3 bucket, which serves as the backend for a static website.
It is triggered hourly to refresh the data.
The Google Cloud Run variant stores results in a Google Cloud Storage bucket.

http://www.inpair.pl

http://inpair.s3-website-eu-west-1.amazonaws.com/


![preview](https://github.com/piotrgo/inpair/assets/4050128/9ee56dbb-4d8e-4840-a0c7-2acc9b2aff13)

## Running locally with Docker
Ensure that the relevant API key is specified in a .env file 
with the environment var for the API key set as shown below
```text
INPOST_API_TOKEN={YOUR_API_TOKEN}
```

Docker commands:
```shell
docker build -t inpost-map-fn .
docker run --env-file .env -p 8080:8080 inpost-map-fn
```

Once the container is built and running, browse to localhost:8080 to see the page load.

*Note:* Docker must be installed for this to succeed, include any cacerts required within
the dockerfile as necessary when running behind a proxy (e.g. ZScaler).