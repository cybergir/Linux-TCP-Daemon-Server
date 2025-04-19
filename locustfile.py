from locust import HttpUser, TaskSet, task, between


class MyTaskSet(TaskSet):
    # Define a set of tasks to be executed by the user.
    host = "http://127.0.0.1:8089"

    @task(1)
    def get_example(self):
        # Sends a GET request to the /example endpoint.
        self.client.get("/example")


class MyUser(HttpUser):
    # Defines a user that will execute tasks defined in MyTaskSet.
    tasks = [MyTaskSet]
    wait_time = between(1, 3)
