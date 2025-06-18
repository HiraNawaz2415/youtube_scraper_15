import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import json
from datetime import datetime

# --- Helper Function to Convert Likes ---
def parse_likes(likes_text):
    if "K" in likes_text:
        return int(float(likes_text.replace('K', '').strip()) * 1000)
    elif "M" in likes_text:
        return int(float(likes_text.replace('M', '').strip()) * 1000000)
    elif "B" in likes_text:
        return int(float(likes_text.replace('B', '').strip()) * 1000000000)
    else:
        return int(likes_text.replace(',', '').strip())

# --- Scroll Page Helper ---
def scroll_down(driver, pause_time=2, max_scrolls=15):
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# --- Streamlit UI ---
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
            # --- Setup Selenium Driver ---
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920x1080")

            driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=chrome_options)
            driver.get(video_url)
            time.sleep(10)  # Wait for full page load

            # --- Title ---
            try:
                title = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.style-scope.ytd-watch-metadata"))
                ).text.strip()
            except:
                title = "Title not found"
            st.subheader("🎬 Title")
            st.write(title)

            # --- Channel Name ---
            try:
                channel = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#channel-name yt-formatted-string"))
                ).text.strip()
            except:
                channel = "Channel name not found"
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
                views = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'views')]"))
                ).text.strip()
            except:
                views = "Views not found"
            st.subheader("👁️ Views")
            st.write(views)

            # --- Likes ---
            try:
                likes_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-toggle-button-renderer[is-icon-button] yt-formatted-string"))
                )
                likes_text = likes_element.text.strip()
                likes = parse_likes(likes_text)
            except Exception as e:
                likes = "Likes not found"
                st.warning(f"⚠️ Error fetching likes: {e}")
            st.subheader("👍 Likes")
            st.write(f"{likes} Likes")

            # --- Description ---
            try:
                show_more = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "tp-yt-paper-button#expand"))
                )
                driver.execute_script("arguments[0].click();", show_more)
                time.sleep(1)
            except:
                pass

            try:
                description_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#description yt-formatted-string"))
                )
                description = description_element.text.strip()
            except:
                description = "Description not found"
            st.subheader("📝 Description")
            st.write(description)

            # --- Comments ---
            try:
                comments_section = driver.find_element(By.CSS_SELECTOR, "#comments")
                driver.execute_script("arguments[0].scrollIntoView();", comments_section)
            except:
                pass
            time.sleep(2)
            scroll_down(driver)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-comment-thread-renderer"))
            )
            comment_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-comment-thread-renderer")

            for element in comment_elements:
                try:
                    comment_text = element.find_element(By.CSS_SELECTOR, "#content-text").text
                    comments.append(comment_text)
                except:
                    continue

            st.success(f"✅ Extracted {len(comments)} comments.")
            for i, comment in enumerate(comments, 1):
                st.write(f"{i}. {comment}")

            # --- Data Export ---
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            video_info = {
                "Title": title,
                "Channel": channel,
                "Subscribers": subs,
                "Views": views,
                "Likes": likes,
                "Description": description,
                "Scraped DateTime": current_datetime
            }

            df_info = pd.DataFrame([video_info])
            df_comments = pd.DataFrame(comments, columns=["Comment"])
            combined_df = pd.concat([df_info, df_comments], axis=1)

            st.subheader("💾 Download Data")

            # CSV
            csv_data = combined_df.to_csv(index=False)
            st.download_button("📊 Download CSV", csv_data, file_name="youtube_data.csv")

            # JSON
            json_data = json.dumps({"video_info": video_info, "comments": comments}, indent=2)
            st.download_button("🗃️ Download JSON", json_data, file_name="youtube_data.json")

            # TXT
            txt_output = f"Title: {title}\nChannel: {channel}\nSubscribers: {subs}\nViews: {views}\nLikes: {likes}\nDescription:\n{description}\n\nComments:\n"
            for i, comment in enumerate(comments, 1):
                txt_output += f"{i}. {comment}\n"
            st.download_button("📄 Download TXT", txt_output, file_name="youtube_data.txt")

        except Exception as e:
            st.error("❌ An error occurred:")
            st.error(str(e))

        finally:
            try:
                driver.quit()
            except:
                pass
