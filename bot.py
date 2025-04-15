import requests
import time
import schedule
import logging
import os
from dotenv import load_dotenv
from datetime import datetime

# === LOAD ENV ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
API_BASE = "https://api.teneo.finance/v1"  # Placeholder URL

if not API_KEY or not WALLET_ADDRESS:
    raise EnvironmentError("Missing API_KEY or WALLET_ADDRESS in .env file")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# === LOGGING ===
logging.basicConfig(
    filename='teneo_bot.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log(msg, level="info"):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    getattr(logging, level)(msg)

ACTIVITY_THRESHOLD = 75
REWARD_THRESHOLD = 1.0
COMPOUND_INTERVAL_MINUTES = 60
FARM_INTERVAL_MINUTES = 15
MAX_RETRIES = 3

def safe_request(method, url, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.request(method, url, headers=HEADERS, timeout=10, **kwargs)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            log(f"Request error: {e} | URL: {url}", level="error")
            time.sleep(2 * (attempt + 1))
    log(f"Max retries reached for {url}", level="error")
    return None

def get_activity_score():
    url = f"{API_BASE}/activity/{WALLET_ADDRESS}"
    data = safe_request("GET", url)
    return data.get("activityScore", 0) if data else 0

def is_peak_time():
    url = f"{API_BASE}/rewards/peak-times"
    data = safe_request("GET", url)
    return data.get("isPeak", False) if data else False

def get_current_rewards():
    url = f"{API_BASE}/rewards/current/{WALLET_ADDRESS}"
    data = safe_request("GET", url)
    rewards = data.get("unclaimed", 0) if data else 0
    log(f"Current unclaimed rewards: {rewards} TENEO")
    return rewards

def get_staking_status():
    url = f"{API_BASE}/staking/status/{WALLET_ADDRESS}"
    data = safe_request("GET", url)
    return data.get("isStaked", False) if data else False

def perform_farming_action(strategy="standard"):
    url = f"{API_BASE}/farm"
    payload = {"wallet": WALLET_ADDRESS, "strategy": strategy}
    data = safe_request("POST", url, json=payload)
    if data:
        log(f"Farming performed with strategy: {strategy}")
    else:
        log("Farming failed", level="error")

def claim_rewards():
    url = f"{API_BASE}/rewards/claim"
    payload = {"wallet": WALLET_ADDRESS}
    data = safe_request("POST", url, json=payload)
    if data:
        log(f"Rewards claimed: {data}")
    else:
        log("Claim failed", level="error")

def stake_rewards():
    url = f"{API_BASE}/staking/stake"
    payload = {"wallet": WALLET_ADDRESS}
    data = safe_request("POST", url, json=payload)
    if data:
        log("Rewards re-staked")
    else:
        log("Re-staking failed", level="error")

def farming_cycle():
    activity = get_activity_score()
    peak = is_peak_time()
    strategy = "peak" if peak else "standard"
    log(f"Strategy selected: {strategy} | Activity: {activity}")
    if activity >= ACTIVITY_THRESHOLD:
        perform_farming_action(strategy)
    else:
        log(f"Activity too low ({activity}), skipping farming.")

def compound_cycle():
    rewards = get_current_rewards()
    if rewards >= REWARD_THRESHOLD:
        claim_rewards()
        time.sleep(5)
        stake_rewards()
        log(f"Compounded {rewards} TENEO into staking.")
    else:
        log("Not enough rewards to compound.")

def check_staking():
    if not get_staking_status():
        log("Wallet not staked. Attempting to stake...")
        stake_rewards()
    else:
        log("Wallet staking is active.")

def start_bot():
    log("Teneo Bot Started ✅")
    schedule.every(FARM_INTERVAL_MINUTES).minutes.do(farming_cycle)
    schedule.every(COMPOUND_INTERVAL_MINUTES).minutes.do(compound_cycle)
    schedule.every(30).minutes.do(check_staking)
    while True:
        try:
            schedule.run_pending()
            time.sleep(5)
        except Exception as e:
            log(f"Bot crashed: {e}", level="error")
            time.sleep(10)

if __name__ == "__main__":
    start_bot()
