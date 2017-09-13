# Use an official Python runtime as a parent image
FROM python:2.7.13-slim

# Set the working directory to /app
WORKDIR /SleekBots/

# Copy the current directory contents into the container at /app
ADD . /SleekBots

# Install any needed packages specified in requirements.txt
RUN pip install -r scripts/requirements.txt

WORKDIR /SleekBots/Sleek@Slack

# Make port 80 available to the world outside this container
#EXPOSE 80

ARG TOKEN
# Define environment variable
# ENV NAME World
ENV PYTHONPATH .
ENV TOKEN $TOKEN

RUN python main.py -cfg DATA/confs/bro.cfg -init -surveys DATA/surveys/
RUN env


# Run app.py when the container launches
CMD ["python", "-u", "main.py", "-cfg", "DATA/confs/bro.cfg", "-api_token_id", "TOKEN", "-connect","-dbg"]
