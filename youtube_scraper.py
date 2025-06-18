import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import json
import re
from datetime import datetime

# --- Likes Parsing Helper Function ---
def parse_likes(likes_text):
    if "K" in likes_text:
        return int(float(likes_text.replace('K', '').strip()) * 1000)
    elif "M" in likes_text:
        return int(float(likes_text.replace('M', '').strip()) * 1000000)
    elif "B" in likes_text:
        return int(float(likes_text.replace('B', '').strip()) * 1000000000)
    else:
        return int(likes_text.replace(',', '').strip())

# --- Scroll Helper Function ---
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

st.markdown("""
    <style>
    .css-10trblm { text-align: center; }
    h1 { animation: pop 1s ease-in-out; }
    @keyframes pop {
      0% { transform: scale(0.5); opacity: 0; }
      50% { transform: scale(1.1); opacity: 1; }
      100% { transform: scale(1); }
    }
    .stAlert {
        border-radius: 12px;
        padding: 20px;
        font-size: 18px;
    }
    .stDownloadButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        margin: 10px 5px;
        cursor: pointer;
        transition: 0.4s;
    }
    .stDownloadButton>button:hover {
        background-color: #45a049;
    }
    .stDownloadButton { animation: fadeIn 2s; }
    @keyframes fadeIn {
      0% { opacity: 0; }
      100% { opacity: 1; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("📽️ YouTube Video Info + Comments Extractor")
video_url = st.text_input("🔗 Enter YouTube Video URL:")

if st.button("Extract Info"):
    if not video_url:
        st.error("❌ Please enter a valid YouTube URL.")
    else:
        st.info("⏳ Scraping YouTube data...")
        comments = []

        try:
            # Set up Selenium WebDriver
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920x1080")
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/lib/chromium-browser/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)

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

            # --- Channel ---
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
                    EC.presence_of_element_located((By.XPATH, "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[2]/ytd-watch-metadata/div/div[2]/div[2]/div/div/ytd-menu-renderer/div[1]/segmented-like-dislike-button-view-model/yt-smartimation/div/div/like-button-view-model/toggle-button-view-model/button-view-model/button/div[2]"))
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
            except Exception as e:
                print(f"Show more button not found or already expanded: {e}")

            try:
                description_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#description yt-formatted-string"))
                )
                description = description_element.text.strip()
            except Exception as e:
                description = "Description not found"
                print(f"Description fetching error: {e}")

            st.subheader("📝 Description")
            st.write(description)

            # --- Scroll and Extract Comments ---
            try:
                comments_section = driver.find_element(By.CSS_SELECTOR, "#comments")
                driver.execute_script("arguments[0].scrollIntoView();", comments_section)
            except:
                st.write("⚠️ Comments section not directly found. Scrolling full page.")
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

            # --- Current Date & Time ---
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # --- Save Outputs ---
            video_info = {
                "Title": title,
                "Channel": channel,
                "Subscribers": subs,
                "Views": views,
                "Likes": likes,
                "Description": description,
                "Scraped Date and Time": current_datetime
            }
            df_info = pd.DataFrame([video_info])
            df_comments = pd.DataFrame(comments, columns=["Comment"])
            combined_df = pd.concat([df_info, df_comments], axis=1)

            # --- CSV ---
            st.subheader("💾 Download Files")
            csv_data = combined_df.to_csv(index=False)
            st.download_button("📊 Download CSV", csv_data, file_name="video_info_and_comments.csv")

            # --- JSON ---
            full_data = {
                "video_info": video_info,
                "comments": comments
            }
            json_data = json.dumps(full_data, indent=2)
            st.download_button("🗃️ Download JSON", json_data, file_name="video_info_and_comments.json")

            # --- TXT ---
            txt_output = f"Title: {title}\nChannel: {channel}\nSubscribers: {subs}\nViews: {views}\nLikes: {likes}\nDescription:\n{description}\n\nComments:\n"
            for i, comment in enumerate(comments, 1):
                txt_output += f"{i}. {comment}\n"
            st.download_button("📄 Download TXT", txt_output, file_name="video_info_and_comments.txt")

        except Exception as e:
            st.error("❌ An error occurred:")
            st.error(str(e))

        finally:
            try:
                driver.quit()
            except:
                pass
