"""REST API & Automation toolkit: APIs, JSON, email, files, scraping, scheduling."""
import json
import logging
import os
import shutil
import smtplib
import time
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup

logging.basicConfig(filename="automation.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
POSTS_URL = "https://jsonplaceholder.typicode.com/posts"
SCRAPE_URL = "https://quotes.toscrape.com/"  # site made for scraping practice


def api_get(url, params=None):
    """HTTP GET with full error handling."""
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print("Error: request timed out.")
    except requests.exceptions.ConnectionError:
        print("Error: no internet connection.")
    except requests.exceptions.HTTPError as e:
        print("HTTP error:", e)
    except ValueError:
        print("Error: response was not valid JSON.")
    logging.error("API call failed: %s", url)
    return None


def weather_dashboard(city):
    geo = api_get(GEO_URL, {"name": city, "count": 1})
    if not geo or not geo.get("results"):
        print("City not found.")
        return
    g = geo["results"][0]
    w = api_get(WEATHER_URL, {"latitude": g["latitude"], "longitude": g["longitude"],
                              "current_weather": "true"})
    if w:
        cw = w["current_weather"]
        print(f"\n=== Weather Dashboard: {g['name']}, {g.get('country', '')} ===")
        print(f"Temperature : {cw['temperature']} C")
        print(f"Wind speed  : {cw['windspeed']} km/h")
        print(f"Time        : {cw['time']}")
        logging.info("Weather fetched for %s", city)


def fetch_posts(limit=5):
    data = api_get(POSTS_URL)
    if data:
        with open("posts.json", "w", encoding="utf-8") as f:
            json.dump(data[:limit], f, indent=2)
        for p in data[:limit]:
            print(f"#{p['id']} {p['title']}")
        print("Saved to posts.json")


def post_request():
    try:
        r = requests.post(POSTS_URL, json={"title": "InternGrow", "body": "Hello", "userId": 1},
                          timeout=10)
        print("POST status:", r.status_code, "->", r.json())
    except requests.exceptions.RequestException as e:
        print("POST failed:", e)


def scrape_quotes():
    try:
        r = requests.get(SCRAPE_URL, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Scraping failed:", e)
        return
    soup = BeautifulSoup(r.text, "html.parser")
    for q in soup.select("div.quote")[:5]:
        print(f'"{q.select_one("span.text").text}" - {q.select_one("small.author").text}')


def send_email(to, subject, body):
    """Set env vars EMAIL_USER and EMAIL_PASS (Gmail app password). Never hardcode passwords."""
    user, pw = os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS")
    if not user or not pw:
        print("Set EMAIL_USER and EMAIL_PASS environment variables first.")
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(user, pw)
            s.send_message(msg)
        print("Email sent.")
        logging.info("Email sent to %s", to)
    except smtplib.SMTPException as e:
        print("Email failed:", e)


def organize_folder(folder):
    """File automation: sort files into sub-folders by extension."""
    if not os.path.isdir(folder):
        print("Folder not found.")
        return
    count = 0
    for name in os.listdir(folder):
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            ext = os.path.splitext(name)[1].lstrip(".").lower() or "no_extension"
            os.makedirs(os.path.join(folder, ext), exist_ok=True)
            shutil.move(p, os.path.join(folder, ext, name))
            count += 1
    print(f"Organized {count} files.")
    logging.info("Organized %d files in %s", count, folder)


def scheduled_weather(city, minutes, runs):
    """Scheduled automation: run the weather job repeatedly."""
    for i in range(runs):
        print(f"\n[Run {i + 1}/{runs}]")
        weather_dashboard(city)
        if i < runs - 1:
            time.sleep(minutes * 60)


def menu():
    while True:
        print("\n===== REST API & Automation =====")
        print("1.Weather dashboard  2.Fetch posts (GET)  3.Send POST request")
        print("4.Scrape quotes  5.Send email  6.Organize folder")
        print("7.Scheduled weather job  0.Exit")
        ch = input("Choose: ").strip()
        if ch == "1": weather_dashboard(input("City: "))
        elif ch == "2": fetch_posts()
        elif ch == "3": post_request()
        elif ch == "4": scrape_quotes()
        elif ch == "5": send_email(input("To: "), input("Subject: "), input("Body: "))
        elif ch == "6": organize_folder(input("Folder path: "))
        elif ch == "7":
            scheduled_weather(input("City: "), float(input("Every N minutes: ")),
                              int(input("How many runs: ")))
        elif ch == "0": break
        else: print("Invalid choice.")


if __name__ == "__main__":
    menu()
