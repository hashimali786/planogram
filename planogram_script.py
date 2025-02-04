import os
import sys
import cv2
import time
import boto3
import pymysql
import requests
import json
import smtplib
import pandas as pd
from tqdm import tqdm
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import dateutil.relativedelta

# Load environment variables for security
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

app = Flask(__name__)


def is_image_corrupted(image_path):
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        return True
    try:
        image = cv2.imread(image_path)
        if image is None or image.shape[0] == 0 or image.shape[1] == 0:
            return True
    except cv2.error:
        return True
    return False


def send_email():
    try:
        con = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database=DB_NAME)
        query = """
            SELECT option_value, option_meta FROM options
            WHERE option_group = 'error_alert' AND option_key = 'email'
        """
        options_data = pd.read_sql(query, con)
        con.close()

        to_emails = options_data["option_value"].iloc[0].split(", ")
        smtp_username = options_data["option_meta"].iloc[0]

        subject = "Plan-o-Gram Script Status Alert"
        body = "This is an alert to check the script status."

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_username
        msg["To"] = ", ".join(to_emails)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(smtp_username, to_emails, msg.as_string())
    except Exception as e:
        print(f"Email sending failed: {e}")


def check_last_insert_time():
    try:
        con = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database=DB_NAME)
        query = "SELECT MAX(created_at) as last_insert FROM image_predictions"
        last_insert_data = pd.read_sql(query, con)
        con.close()

        last_insert_time = last_insert_data['last_insert'][0] if not last_insert_data.empty else None

        if last_insert_time and datetime.now() - last_insert_time > timedelta(hours=1):
            send_email()
    except Exception as e:
        print(f"Error checking last insert time: {e}")


@app.route('/images_script')
def images_script():
    try:
        con = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database=DB_NAME)
        cursor = con.cursor()

        check_last_insert_time()

        query = "SELECT end_id FROM image_process_logs ORDER BY image_process_log_id DESC LIMIT 1"
        last_id_data = pd.read_sql(query, con)
        start_id = int(last_id_data['end_id'].iloc[0]) - 1 if not last_id_data.empty else 0

        image_query = f"""
            SELECT fridge_images.*, fridge_types.fridge_type as fridge_type_name
            FROM fridge_images
            INNER JOIN fridge_types ON fridge_images.fridge_type = fridge_types.fridge_type_id
            WHERE fridge_images.image_id > {start_id} AND fridge_images.status = 1
            ORDER BY fridge_images.image_id LIMIT 10
        """
        fridge_images = pd.read_sql(image_query, con)

        if fridge_images.empty:
            return jsonify({"status": "No data to process"}), 200

        download_directory = "/var/www/html/downloaded_images/"
        os.makedirs(download_directory, exist_ok=True)

        failed_downloaded_df = pd.DataFrame(columns=['image', 'full_url'])
        fixed_url = 'https://cdn.example.com/uploads/plan/'

        for index, row in fridge_images.iterrows():
            image_filename = row['image']
            full_url = fixed_url + image_filename
            save_path = os.path.join(download_directory, image_filename)

            try:
                response = requests.get(full_url)
                if response.status_code == 200:
                    with open(save_path, 'wb') as file:
                        file.write(response.content)
                else:
                    failed_downloaded_df = pd.concat(
                        [failed_downloaded_df, pd.DataFrame({'image': [image_filename], 'full_url': [full_url]})],
                        ignore_index=True
                    )
            except Exception as e:
                failed_downloaded_df = pd.concat(
                    [failed_downloaded_df, pd.DataFrame({'image': [image_filename], 'full_url': [full_url]})],
                    ignore_index=True
                )

        fridge_images = fridge_images[~fridge_images['image'].isin(failed_downloaded_df['image'])]
        for image_value in failed_downloaded_df['image']:
            update_query = f"UPDATE fridge_images SET process_status = 9 WHERE image = '{image_value}'"
            cursor.execute(update_query)

        con.commit()
        con.close()
        return jsonify({"status": "Processing complete"}), 200
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(debug=True)
