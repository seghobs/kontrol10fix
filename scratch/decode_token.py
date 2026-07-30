import base64
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("decode_token")

# Let's take the token from the test runner:
# "Bearer IGT:2:eyJkc191c2VyX2lkIjoiNDgyNDExNjEzNTYiLCJzZXNzaW9uX2tleSI6Ik9SMzVnM1BZZGZocEExIiwiY29va2llcyI6Im1pZD1aeDlPTlFBQUFBR1c1WnpsSGFmZVRWNHI7c2Vzc2lvbmlkPTQ4MjQxMTYxMzU2JTNBcXp2OG1UdzEwSmw0SkYlM0ExOSJ9"
token = "Bearer IGT:2:eyJkc191c2VyX2lkIjoiNDgyNDExNjEzNTYiLCJzZXNzaW9uX2tleSI6Ik9SMzVnM1BZZGZocEExIiwiY29va2llcyI6Im1pZD1aeDlPTlFBQUFBR1c1WnpsSGFmZVRWNHI7c2Vzc2lvbmlkPTQ4MjQxMTYxMzU2JTNBcXp2OG1UdzEwSmw0SkYlM0ExOSJ9"

base64_part = token.split("Bearer IGT:2:")[1]
decoded = base64.b64decode(base64_part).decode("utf-8")
logger.info("Decoded: %s", decoded)
