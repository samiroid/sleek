#docker build -t sleekbot .
sudo docker build --build-arg TOKEN=$SLEEK_BETA_TOKEN -t sleekbot -f Dockerfile_Sleek . 