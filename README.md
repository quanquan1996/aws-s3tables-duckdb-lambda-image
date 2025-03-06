sudo docker buildx build --platform linux/amd64 --provenance=false -t docker-image:xxxx .
sudo docker tag docker-image:xxxx xxxxxx.dkr.ecr.us-west-2.amazonaws.com/xxxxx:latest
sudo docker tag docker-image:xxxx xxxx.dkr.ecr.us-west-2.amazonaws.com/xxxxx:latest
