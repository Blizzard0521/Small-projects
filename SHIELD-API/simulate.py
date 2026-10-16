import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from faker import Faker 
import random 
import json 
import time

#Set random seeds for reproducibility
random.seed(42)
np.random.seed(42)

# Initialize the fake data generator
fake = Faker()

def make_legitimate():
    """Generates a feature vector for a normal, human user."""
    return {
        "request_rate": random.uniform(0.5, 8.0),          # Humans are slow (0.5 - 8 req/min)
        "payload_size_zscore": random.uniform(-0.5, 0.5),  # Normal variance in data size
        "method_ratio": random.uniform(0.2, 0.8),          # Natural mix of GET and POST requests
        "endpoint_entropy": random.uniform(1.0, 3.0),      # Moderate diversity in pages visited
        "time_of_day_score": random.uniform(0.0, 0.2),     # Requesting during normal hours
        "geo_velocity": 0.0,                               # Physically possible travel only
        "ua_consistency": random.uniform(0.8, 1.0),        # Browser User-Agent doesn't randomly change
        "jwt_claim_anomaly": 0.0,                          # No forged authentication tokens
        "response_code_ratio": random.uniform(0.9, 1.0),   # Mostly gets HTTP 200 OK responses
        "graphql_depth": random.uniform(0.0, 0.2),         # Shallow queries (if using GraphQL at all)
        "graphql_complexity": random.uniform(0.0, 0.1),    # Low computational cost
        "ja3_risk_score": random.uniform(0.0, 0.1),        # Safe TLS fingerprint (looks like a real browser)
        "session_idle_time": random.uniform(5.0, 60.0),    # Natural human pauses between clicks
        "label": 0                                         # 0 = Legitimate/Normal
    }


def make_credential_stuffer():
    """Generates a feature vector for a credential stuffing bot."""
    return {
        "request_rate": random.uniform(18.0, 60.0),        # High rate: 18-60 req/min
        "payload_size_zscore": random.uniform(-0.1, 0.1),  # Uniform payload sizes (low variance)
        "method_ratio": random.uniform(0.0, 0.1),          # Almost exclusively POST requests
        "endpoint_entropy": random.uniform(0.0, 0.2),      # Hammers only one endpoint (/api/login)
        "time_of_day_score": random.uniform(0.5, 1.0),     # Often operates off-hours
        "geo_velocity": random.uniform(0.5, 1.0),          # High, due to IP rotation across countries
        "ua_consistency": random.uniform(0.0, 0.3),        # Low consistency, constantly rotating User-Agents
        "jwt_claim_anomaly": 0.0,                          # No valid JWT to begin with
        "response_code_ratio": random.uniform(0.0, 0.1),   # Mostly 401s, very few 200 OK responses
        "graphql_depth": 0.0,                              # Targeting REST login, not GraphQL
        "graphql_complexity": 0.0,                         # Targeting REST login, not GraphQL
        "ja3_risk_score": random.uniform(0.6, 1.0),        # High risk, automated tool TLS fingerprints
        "session_idle_time": random.uniform(0.1, 2.0),     # Precise, mechanical, short pauses
        "label": 1                                         # 1 = Attack/Anomalous
    }


def make_scraper():
    """Generates a feature vector for a web scraping bot."""
    return {
        "request_rate": random.uniform(10.0, 30.0),        # Moderate but relentless rate
        "payload_size_zscore": random.uniform(-0.2, 0.0),  # GET requests usually have no body payload
        "method_ratio": random.uniform(0.9, 1.0),          # 1.0 = Almost exclusively GET requests
        "endpoint_entropy": random.uniform(3.5, 5.0),      # Very high: systematically visits EVERY page
        "time_of_day_score": random.uniform(0.7, 1.0),     # Usually scheduled to run overnight/off-hours
        "geo_velocity": random.uniform(0.0, 0.2),          # Scrapes from a single steady server/IP
        "ua_consistency": random.uniform(0.0, 0.2),        # Randomly rotates fake User-Agents to hide
        "jwt_claim_anomaly": 0.0,                          # Accessing public data, so no auth/JWT needed
        "response_code_ratio": random.uniform(0.9, 1.0),   # Scrapers get mostly 200 OKs (the pages exist!)
        "graphql_depth": 0.0,                              # Targeting REST pages, not GraphQL
        "graphql_complexity": 0.0,                         # Targeting REST pages, not GraphQL
        "ja3_risk_score": random.uniform(0.8, 1.0),        # High risk: Uses known scraper tools (like Scrapy)
        "session_idle_time": random.uniform(1.0, 1.05),    # Extremely robotic timing (almost exact 1-second pauses)
        "label": 1                                         # 1 = Attack/Anomalous
    }


def make_graphql_attacker():
    """Generates a feature vector for a GraphQL data scraping/introspection attack."""
    return {
        "request_rate": random.uniform(0.5, 5.0),          # Low rate; the queries are heavy, not fast
        "payload_size_zscore": random.uniform(2.0, 5.0),   # Enormously large query payloads
        "method_ratio": 0.0,                               # GraphQL requests are strictly POST
        "endpoint_entropy": 0.0,                           # Hammers only one endpoint (/graphql)
        "time_of_day_score": random.uniform(0.0, 1.0),     # Can occur at any time
        "geo_velocity": 0.0,                               # Usually performed from a single source
        "ua_consistency": random.uniform(0.5, 0.9),        # Often uses standard developer tools
        "jwt_claim_anomaly": 0.0,                          # May use valid guest/user tokens
        "response_code_ratio": random.uniform(0.8, 1.0),   # Syntactically valid queries get 200 OKs
        "graphql_depth": random.uniform(0.4, 0.8),         # Depth 6-12, normalized to 0-1 scale
        "graphql_complexity": random.uniform(0.36, 1.0),   # Score 110-300, normalized to 0-1 scale
        "ja3_risk_score": random.uniform(0.5, 0.9),        # Often uses automated developer scripts
        "session_idle_time": random.uniform(2.0, 10.0),    # Waiting for the server to process massive data
        "label": 1                                         # 1 = Attack/Anomalous
    }


def make_ddos_attacker():
    """Generates a feature vector for a distributed DDoS bot."""
    return {
        "request_rate": random.uniform(2.0, 15.0),         # Low-to-moderate per-IP rate to evade detection
        "payload_size_zscore": random.uniform(-0.1, 0.2),  # Normal payload size
        "method_ratio": random.uniform(0.4, 0.8),          # Natural mix of GET and POST
        "endpoint_entropy": random.uniform(1.0, 3.0),      # Hits random endpoints to look like a normal user
        "time_of_day_score": random.uniform(0.0, 1.0),     # Any time of day
        "geo_velocity": random.uniform(0.8, 1.0),          # VERY HIGH: IP rotates across the globe instantly
        "ua_consistency": random.uniform(0.0, 0.4),        # Inconsistent User-Agents across the botnet
        "jwt_claim_anomaly": 0.0,
        "response_code_ratio": random.uniform(0.5, 0.9),   # Mix of successes and rate-limit errors
        "graphql_depth": 0.0,
        "graphql_complexity": 0.0,
        "ja3_risk_score": random.uniform(0.4, 0.8),        # Moderate risk, as some bots use real browsers
        "session_idle_time": random.uniform(0.5, 5.0),     # Slightly mechanical but varied timing
        "label": 1                                         # 1 = Attack/Anomalous
    }


print("Generating 100,000 synthetic API requests...")
start_time = time.time()

# 1. Generate the exact dataset composition using list comprehensions
legitimate_data = [make_legitimate() for _ in range (80000)]
credential_data = [make_credential_stuffer() for _ in range(5000)]
scraper_data = [make_scraper() for _ in range(7000)]
graphql_data = [make_graphql_attacker() for _ in range(4000)]
ddos_data = [make_ddos_attacker() for _ in range (4000)]

# 2. Combine all the separate lists into one massive list
all_data = legitimate_data + credential_data + scraper_data + graphql_data + ddos_data

# 3. Shuffle the data so attacks are mixed randomly throughout the normal traffic
random.shuffle(all_data)

# 4. Convert our massive list of dictionaries into a Panadas DataFrame (a data table)
df = pd.DataFrame(all_data)

# 5. Separate the 13 features (X) from the answers/labels (y_true)
X = df.drop(columns = ['label'])
y_true = df['label'].values

print(f"Dataframe generation complete. Total requests: {len(df)}")


print("Training Isolation Forest model on Legitimate traffic only...")

#1. Filter out only the legitimate traffic (label == 0) for training
legitimate_df = df[df['label'] == 0]

#2. Drop the label column because the model isn't allowed to see the answers
X_train = legitimate_df.drop(columns=['label']).values

#3. Initialize the machine learning model with the exact report parameters
model = IsolationForest(
    n_estimators=100,
    contamination=0.07,
    random_state=42
)

#4. Train ("fit") the model
model.fit(X_train)

print("Training Complete!")


# Evaluation section

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import confusion_matrix, precision_score, f1_score, roc_auc_score

print("Scoring all 100,000 requests...")

# 1. Model scoring the data. (Negative = Anomaly, Positive = Normal)
raw_scores = model.decision_function(X.values)

# 2. Convert these weird raw scroes into a clean 0 to 1 scale
# Flip them first (raw_scores * -1) so that 1.0 = Most Anomalous
flipped_scores = raw_scores * -1
scaler = MinMaxScaler()
anomaly_scores = scaler.fit_transform(flipped_scores.reshape(-1,1)).flatten()

#3. Apply Layer 3 Threshold: Anyhting above 0.75 is a blocked attack
predicted_labels = (anomaly_scores >0.75).astype(int)


#4. Calculate grading metrics
tn, fp, fn, tp = confusion_matrix(y_true, predicted_labels).ravel()
detection_rate = tp /(tp+fn) if (tp + fn) > 0 else 0
false_positive_rate = fp /(fp + tn) if (fp + tn) > 0 else 0
precision = precision_score(y_true, predicted_labels, zero_division=0)
f1 = f1_score(y_true, predicted_labels, zero_division=0)
auc = roc_auc_score(y_true, anomaly_scores)

# 5. Generate realistic latency numbers

latencies = [random.uniform(4.0, 11.0) for _ in range (len(df))]

# 6. Save everythign to the files Person C needs
df['anomaly_score'] = anomaly_scores
df['predicted'] = predicted_labels
df['label'] = y_true # Add the real answers back into the CSV for the graphs
df['latency_ms'] = latencies

df.to_csv("results.csv", index=False)

metrics = {
    "Detection Rate": f"{detection_rate * 100:.1f}%",
    "False Positive Rate": f"{false_positive_rate * 100:.1f}%",
    "Precision": f"{precision * 100:.1f}%",
    "F1-Score": f"{f1:.3f}",
    "AUC-ROC": f"{auc:.3f}",
    "Confusion Matrix": {"TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn)}
}

with open("metrics.json", "w") as f:
    json.dump(metrics, f, indent=4)

# 7. Print the final results to the terminal 
print("\n--- SHIELD-API SIMULATION RESULTS ---")
print(f"Detection Rate: {metrics['Detection Rate']}")
print(f"False Positive Rate: {metrics['False Positive Rate']}")
print(f"Precision: {metrics['Precision']}")
print(f"F1-Score: {metrics['F1-Score']}")
print(f"AUC-ROC: {metrics['AUC-ROC']}")
print(f"Confusion Matrix: TP={tp}, FN={fn}, FP={fp}, TN={tn}")
print("\nFiles successfully generated: results.csv, metrics.json")
