import os
from locust import HttpUser, task, between


class UserBehavior(HttpUser):
    # Defines the behavior of a user.
    wait_time = between(1, 5)
    host = os.getenv("LOCUST_HOST", "http://127.0.0.1:8089")

    @task(1)
    def test_query(self):
        # Sends a GET request to the root URL and prints the response.
        response = self.client.get("/")
        print("Response:", response.text)


# Configuration for Locust
class WebsiteUser(HttpUser):
    # Configures settings for the Locust user.
    wait_time = between(1, 5)
    host = os.getenv("LOCUST_HOST", "http://127.0.0.1:8089")
    tasks = [UserBehavior]  # Assign UserBehavior to this user
