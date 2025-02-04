# Planogram for bottle detection 

# Overview
This script is a Flask-based image processing system that:

Fetches images from a database that need processing.
Downloads images from a CDN (Content Delivery Network).
Validates images to check for corruption.
Processes images using a YOLO object detection model.
Updates the database with processed results.
Sends email alerts if the script is not running as expected.
Key Components
# 1. Imports
The script imports multiple libraries for various tasks:

Data Handling: pandas
Deep Learning: ultralytics.YOLO (for object detection)
Progress Bar: tqdm
Web Framework: Flask
Image Processing: cv2, PIL
Database Connection: pymysql
Networking: requests
Email Notifications: smtplib
Amazon S3: boto3 (though not used in the visible code)
# 2. Database Connection (DBHelper)
The script initializes a database helper instance (con1 = DBHelper()) to manage database connections.
# 3. Flask Application Setup
app = Flask(__name__) initializes the Flask app to expose an API endpoint.
Functions & Their Purpose
# 1. Checking Image Corruption (is_image_corrupted)
python
Copy
Edit
def is_image_corrupted(image_path):
    if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
        return True
    try:
        image = cv2.imread(image_path)
        if image is None or image.shape[0] == 0 or image.shape[1] == 0:
            return True
    except cv2.error as e:
        return True
    return False
Ensures that the image is readable and has valid dimensions.
Uses OpenCV (cv2.imread) to check if the image is corrupted.
# 2. Sending Email Alerts (send_email)
python
Copy
Edit
def send_email(con):
    query = """
        SELECT option_key, option_value, option_meta
        FROM options
        WHERE option_group = 'error_alert' AND option_key = 'email'
    """
    options_data = pd.read_sql(query, con)

    to_emails = options_data["option_value"].iloc[0].split(", ")
    smtp_username = options_data["option_meta"].iloc[0]
    smtp_server = ".gmail.com"
    smtp_port = 000
    smtp_password = ""

    subject = "Plan-o-Gram Script Status Alert"
    body = "This is an alert to check if the Plan-o-Gram script is running or has encountered an error."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_username
    msg["To"] = ", ".join(to_emails)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, to_emails, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
Queries the database for recipient email addresses.
Sends an alert email if the script stops working.
# 3. Checking Last Image Insert Time (check_last_insert_time)
python
Copy
Edit
def check_last_insert_time(con):
    last_insert_query = "SELECT MAX(created_at) as last_insert FROM image_predictions"
    last_insert_data = pd.read_sql(last_insert_query, con)

    last_insert_time = last_insert_data['last_insert'][0] if not last_insert_data.empty else None

    if last_insert_time and datetime.now() - last_insert_time > timedelta(hours=1):
        send_email(con)
Retrieves the last inserted image timestamp from the image_predictions table.
If no new images are processed within the last hour, it sends an email alert.
# 4. Image Processing API (/images_script Endpoint)
python
Copy
Edit
@app.route('/images_script')
def images_script():
Step 1: Connect to the database

python
Copy
Edit
con = pymysql.connect(host=con1.host, user=con1.user, password=con1.password, port=con1.port, database=con1.db)
con.autocommit = False
mycursor = con.cursor()
Step 2: Check last inserted image timestamp

python
Copy
Edit
check_last_insert_time(con)
Step 3: Get last processed image ID

python
Copy
Edit
end_for_start_id = pd.read_sql(SQL Query)
start_id = int((end_for_start_id['end_id']).to_string(index=False)) - 1
# Step 4: Fetch images that need processing

python
Copy
Edit
fridge_images = pd.read_sql(
    SQL Query )
# Step 5: Download images from the CDN

python
Copy
Edit
fixed_url = 'URL'
download_directory = "URL"
os.makedirs(download_directory, exist_ok=True)

for index, row in fridge_images.iterrows():
    image_filename = row['image']
    full_url = fixed_url + image_filename
    save_path = os.path.join(download_directory, image_filename)

    try:
        response = requests.get(full_url)
        if response.status_code == 200:
            with open(save_path, 'wb') as file:
                file.write(response.content)
    except Exception as e:
        print(f"Error downloading image: {str(e)}")
# Step 6: Remove corrupted images

python
Copy
Edit
fridge_images = fridge_images[~fridge_images['image'].isin(failed_downloaded_df['image'])]
# Step 7: Process Images using YOLO

python
Copy
Edit
model = YOLO("best.pt")
for index, row in fridge_images.iterrows():
    image_filename = row['image']
    image_id = row['image_id']
    full_image_path = os.path.join(download_directory, image_filename)

    if is_image_corrupted(full_image_path):
        mycursor.execute(Query")
        con.commit()
        continue

    results = model.predict(full_image_path)  # Run YOLO model on the image

    # Store results in the database
    mycursor.execute(Query)
    con.commit()
# Summary
Database Connection: Connects to MySQL and fetches unprocessed images.
Image Download: Retrieves images from a CDN and stores them locally.
Corruption Check: Ensures images are valid before processing.
YOLO Model Processing: Runs object detection using a pre-trained best.pt YOLO model.
Database Update: Updates process status in the database.
Error Handling: If the script does not process images for over an hour, it sends an alert email.
Potential Enhancements
Store YOLO detection results in a structured format.
Use multi-threading to speed up image processing.
