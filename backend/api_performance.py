import time
import httpx
import statistics

BASE_URL = "http://localhost:8000"
NUM_REQUESTS = 10

TEST_PROFILE = {
    "skills": ["python", "sql", "tensorflow", "pytorch", "aws"],
    "age": 23,
    "gender": "Male",
    "degree_level": "Bachelor",
    "field_of_study": "Data Science",
    "gpa": 3.5,
    "years_experience": 1,
    "python": 1,
    "java": 0,
    "c_cpp": 0,
    "sql": 1,
    "machine_learning": 1,
    "data_analysis": 1,
    "cloud_computing": 1,
    "cybersecurity": 0,
    "web_development": 0,
    "devops": 0,
    "networking": 0,
    "communication": 4,
    "leadership": 3,
    "problem_solving": 5,
    "teamwork": 4,
    "adaptability": 3,
}

def benchmark_api():
    with httpx.Client(timeout=60.0) as client:
        try:
            client.get(f"{BASE_URL}/health")
        except httpx.ConnectError:
            print(f"Server at {BASE_URL} is unreachable.")
            return

        print(f"Benchmarking /recommend ({NUM_REQUESTS} requests)...")
        rec_latencies = []
        session_id = None
        
        for _ in range(NUM_REQUESTS):
            start = time.perf_counter()
            res = client.post(f"{BASE_URL}/recommend", json=TEST_PROFILE)
            res.raise_for_status()
            rec_latencies.append((time.perf_counter() - start) * 1000)
            
            # Capture a valid session_id from the first successful response to use in the chat test
            if not session_id:
                session_id = res.json().get("session_id")
                
        print(f"  Average: {statistics.mean(rec_latencies):.2f} ms")
        print(f"  Min:     {min(rec_latencies):.2f} ms")
        print(f"  Max:     {max(rec_latencies):.2f} ms\n")

        if not session_id:
            print("Skipping /chat benchmark: No session_id returned from /recommend.")
            return

        chat_payload = {
            "session_id": session_id,
            "history": [],
            "message": "What should I learn next?",
            "deep": False,
        }

        print(f"Benchmarking /chat ({NUM_REQUESTS} requests) with user simulation...")
        chat_latencies = []
        
        for i in range(NUM_REQUESTS):
            start = time.perf_counter()
            res = client.post(f"{BASE_URL}/chat", json=chat_payload)
            res.raise_for_status()
            latency = (time.perf_counter() - start) * 1000
            chat_latencies.append(latency)
            print(f"  Request {i+1}: {latency:.2f} ms")

            if i < NUM_REQUESTS - 1:
                time.sleep(4)

        print(f"  Average: {statistics.mean(chat_latencies):.2f} ms")
        print(f"  Min:     {min(chat_latencies):.2f} ms")
        print(f"  Max:     {max(chat_latencies):.2f} ms")

if __name__ == "__main__":
    benchmark_api()
