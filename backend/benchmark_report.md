# Performance Evaluation Report - IT Career Advisor

Generated: 2026-05-31 22:08:44 ( Казахское время )

This report presents a thorough latency audit of the IT Career Recommendation System. All measurements are processed using vectorized statistical tools to ensure scientific accuracy.

---

## 1. End-to-End API /recommend Endpoint

Measures full HTTP pipeline overhead, including request parsing, validation, multi-model execution, database record writing, and JSON serialization.

| Metric | Latency (ms) | Description |
| :--- | :---: | :--- |
| **Mean** | 1975.31 | Arithmetic average of execution times |
| **Median (p50)** | 688.67 | 50% of requests are faster than this value |
| **95th Percentile (p95)** | 5196.03 | Real-world SLA benchmark (extreme latency bound) |
| **Min / Max** | 558.49 / 5695.85 | Absolute minimum and peak execution limits |
| **Standard Deviation** | 1918.66 | Latency jitter and response stability indicator |

---

## 2. Internal Microservice Latency Breakdown

Profiling isolated internal pipeline steps (average values over all test runs):

| Submodule / Operation | Mean Latency (ms) | Median Latency (ms) | p95 Latency (ms) | Std Dev (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **Skill Matcher** | 1.19 | 1.35 | 1.43 | 0.24 |
| **Classifier** | 599.10 | 603.99 | 645.69 | 38.94 |
| **Demand** | 0.14 | 0.13 | 0.17 | 0.02 |
| **Course Finder** | 0.23 | 0.20 | 0.36 | 0.08 |
| **Context Builder** | 0.35 | 0.33 | 0.45 | 0.06 |
| **Db Save** | 9.84 | 9.84 | 12.51 | 1.97 |

---

## 3. Course Filtering Engine Performance

Evaluation under different skill counts in the gap list, various localization targets, and user-selected platform or difficulty criteria.

| Scenario | Language | Number of Skills | Mean Latency (ms) | p95 Latency (ms) |
| :--- | :---: | :---: | :---: | :---: |
| 1 Skill, No Filters | en | 1 | 2.83 | 3.73 |
| 3 Skills, No Filters | ru | 3 | 107.62 | 422.33 |
| 5 Skills, No Filters | en | 5 | 120.55 | 471.88 |
| 10 Skills, No Filters | en | 10 | 215.17 | 850.96 |
| 5 Skills, Platforms Filter | en | 5 | 204.98 | 811.24 |
| 5 Skills, Difficulty Level Filter | ru | 5 | 180.56 | 713.20 |
| 5 Skills, Combined Filters | kk | 5 | 195.38 | 772.94 |

---

## 4. LLM Chat and Streaming Responsiveness

Measurements for text chat and chunk-based streaming generation.

* **LLM Engine Status**: REAL API KEY CONFIGURED

| Operation | Mean Latency (ms) | Median (p50) (ms) | p95 Latency (ms) |
| :--- | :---: | :---: | :---: |
| **Standard Non-Streaming Chat** | 3210.62 | 1193.76 | 6694.59 |
| **Streaming: Time-to-First-Token (TTFT)** | 547.11 | 538.49 | 568.54 |
| **Streaming: Full Response Generation** | 861.84 | 964.53 | 996.52 |

---

## 5. Summary Findings & Optimization Tips

1. **Course Finder & Routing Bottleneck**: Course matching is the primary local contributor to overall latency because it performs regex substring queries against the courses database.
   * *Optimization*: Introduce local memory caching for common skills, or migrate matching searches to Pandas vector indices or a relational SQLite full-text indexing pattern (FTS5).
2. **Database Save overhead**: Writing the full roadmap and courses payload to SQLite on every recommendation call takes a substantial amount of time.
   * *Optimization*: Write database entries asynchronously via a background task so it doesn't block the HTTP response return thread.
3. **LLM Jitter**: LLM request processing is highly dependent on network quality and remote provider load. Using a streaming structure with standard `/chat/stream` improves perceived speed dramatically, reducing user wait times to a **547.1 ms** TTFT.
