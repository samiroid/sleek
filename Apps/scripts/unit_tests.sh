pytest tests/test_LocalBackend.py -x -v &&
pytest tests/test_KafkaBackend.py -x -v &&

pytest tests/test_Sleek.py -x -v &&
pytest tests/test_Slack.py -x -v 