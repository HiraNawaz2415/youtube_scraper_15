import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import json
from datetime import datetime

# --- Likes Parsing Helper ---
def parse_likes(likes_text):
    if "K" in likes_text:
        return int(float(likes_text.replace('K', '').strip()) * 1_000)
    if "M" in likes_text:
        return int(float(likes_text.replace('M', '').strip()) * 1_000_000)
    if "B" in likes_text:
        return int(float(likes_text.replace('B', '').strip()) * 1_000_000_000)
    return int(likes_text.replace(',', '').strip())

# --- Scroll Helper ---
def scroll_down(driver, pause_time=2, max_scrolls=15):
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# --- Streamlit UI Setup ---
st.set_page_config(page_title="YouTube Scraper")
st.title("📽️ YouTube Video Info + Comments Extractor")
video_url = st.text_input("🔗 Enter YouTube Video URL:")

if st.button("Extract Info"):
    if not video_url:
        st.error("❌ Please enter a valid YouTube URL.")
    else:
        st.info("⏳ Scraping YouTube data...")
        comments = []

        try:
            # --- Selenium Driver Initialization ---
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920x1080")
            # If on Streamlit Cloud, uncomment and adjust:
            # chrome_options.binary_location = "/usr/bin/chromium-browser"

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            driver.get(video_url)
            time.sleep(8)  # allow page to load

            # --- Title ---
            try:
                title_el = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title"))
                )
                title = title_el.text.strip()
            except:
                title = "Title not found"
            st.subheader("🎬 Title")
            st.write(title)

            # --- Channel ---
            try:
                channel = driver.find_element(By.CSS_SELECTOR, "#channel-name yt-formatted-string").text.strip()
            except:
                channel = "Channel not found"
            st.subheader("📺 Channel")
            st.write(channel)

            # --- Subscribers ---
            try:
                subs = driver.find_element(By.CSS_SELECTOR, "#owner-sub-count").text.strip()
            except:
                subs = "Subscribers not found"
            st.subheader("👥 Subscribers")
            st.write(subs)

            # --- Views ---
            try:
                views = driver.find_element(By.XPATH, "//span[contains(text(),'views')]").text.strip()
            except:
                views = "Views not found"
            st.subheader("👁️ Views")
            st.write(views)

            # --- Likes ---
            try:
                likes_el = driver.find_element(
                    By.CSS_SELECTOR,
                    "ytd-toggle-button-renderer:nth-of-type(1) #text"
                )
                likes = parse_likes(likes_el.text.strip())
            except:
                likes = "Likes not found"
            st.subheader("👍 Likes")
            st.write(likes)

            # --- Description ---
            try:
                expand = driver.find_element(By.CSS_SELECTOR, "tp-yt-paper-button#expand")
                driver.execute_script("arguments[0].click();", expand)
                time.sleep(1)
            except:
                pass
            try:
                desc = driver.find_element(By.CSS_SELECTOR, "#description yt-formatted-string").text.strip()
            except:
                desc = "Description not found"
            st.subheader("📝 Description")
            st.write(desc)

            # --- Comments ---
            try:
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                scroll_down(driver)
                threads = driver.find_elements(By.CSS_SELECTOR, "ytd-comment-thread-renderer")
                for t in threads:
                    try:
                        txt = t.find_element(By.CSS_SELECTOR, "#content-text").text
                        comments.append(txt)
                    except:
                        pass
            except:
                st.warning("⚠️ Could not load comments.")

            st.success(f"✅ Extracted {len(comments)} comments")
            for i, c in enumerate(comments, 1):
                st.write(f"{i}. {c}")

            # --- Export Data ---
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            info = {
                "Title": title,
                "Channel": channel,
                "Subscribers": subs,
                "Views": views,
                "Likes": likes,
                "Description": desc,
                "Scraped At": now
            }

            df_info = pd.DataFrame([info])
            df_comments = pd.DataFrame(comments, columns=["Comment"])
            df = pd.concat([df_info, df_comments], axis=1)

            st.subheader("💾 Download Results")
            st.download_button("📊 CSV", df.to_csv(index=False), "youtube_data.csv")
            st.download_button("🗃️ JSON", json.dumps({"info": info, "comments": comments}, indent=2), "youtube_data.json")
            txt = f"{json.dumps(info, indent=2)}\n\nComments:\n" + "\n".join(f"{i}. {c}" for i,c in enumerate(comments,1))
            st.download_button("📄 TXT", txt, "youtube_data.txt")

        except Exception as e:
            st.error("❌ An error occurred:")
            st.error(str(e))

        finally:
            try:
                driver.quit()
            except:
                pass
