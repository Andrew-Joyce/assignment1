# Import necessary modules for the application including Flask, Firestore, and Google Cloud Storage.
# Flask is used for creating the web application.
# Firestore is used for interacting with the Firestore database.
# Google Cloud Storage is used for storing user images and message images.
from flask import Flask, session, redirect, url_for, render_template, request, flash
from werkzeug.utils import secure_filename
from google.cloud import firestore, storage
import datetime, logging
from google.api_core.exceptions import GoogleAPIError
import time


# Initialises Flask app and set a secret key for session management.
app = Flask(__name__)
app.secret_key = "95871372a"

# Initialises Firestore client to interact with the database.
db = firestore.Client()

# Redirect users to the login page by default.
@app.route('/')
def index():
    return redirect(url_for('login'))

# Handles user login functionality, including processing login requests and rendering the login page.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id'] 
        password = request.form['password']
        
        users_ref = db.collection('users')
        query = users_ref.where('id', '==', user_id)
        results = query.stream()
        
        user = next(results, None)
        if user:
            user_data = user.to_dict()
            if user_data.get('password') == password:
                session['user_id'] = user_id
                session['username'] = user_data.get('username', 'No username')  # Provide a default value in case it's not set
                session['profile_image_url'] = user_data.get('profile_image_url', url_for('static', filename='default_profile.png'))  
                return redirect(url_for('forum'))
        
        flash('ID or password is invalid', 'error')
        return render_template('login.html')
    else:
        return render_template('login.html')
    
# Handles user registration, including processing registration requests and rendering the registration page.
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['id']
        username = request.form['username']
        password = request.form['password']
        user_image = request.files['userImage']

        if user_image:
            storage_client = storage.Client()
            bucket = storage_client.bucket('ass_cloud1')
            blob = bucket.blob(f"user_images/{user_id}")
            blob.upload_from_file(user_image, content_type=user_image.content_type)
            blob.make_public()
            image_url = blob.public_url
        else:
            image_url = None  

        result = perform_register(user_id, username, password, image_url, db)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('login'))
        else:
            flash(result['message'], 'error')
            return render_template('register.html')
    else:
        return render_template('register.html')

# Displays the forum page, including handling user authentication and fetching forum messages.
@app.route('/forum')
def forum():
    if 'user_id' not in session: 
        return redirect(url_for('login'))

    user_ref = db.collection('users').document(session['user_id'])
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        session['profile_image_url'] = user_data.get('profile_image_url', url_for('static', filename='default_profile.png'))
    else:
        session['profile_image_url'] = url_for('static', filename='default_profile.png')

    messages = fetch_messages()
    for message in messages:
        user_ref = db.collection('users').document(message['user_id'])
        user_doc = user_ref.get()
        if user_doc.exists:
            message_user_data = user_doc.to_dict()
            message['profile_image_url'] = message_user_data.get('profile_image_url', session['profile_image_url'])
        else:
            message['profile_image_url'] = session['profile_image_url']

    return render_template('forum.html', username=session.get('username', 'Guest'), profile_image_url=session['profile_image_url'], messages=messages)


# Post a message to the forum, including handling authentication and uploading images.
@app.route('/post-message', methods=['POST'])
def post_message():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    subject = request.form.get('subject', '')
    message_text = request.form.get('message', '')
    image = request.files.get('image') 

    doc_ref = db.collection('messages').document()
    doc_ref.set({
        'user_id': session['user_id'], 
        'username': session['username'],
        'subject': subject,
        'message_text': message_text,
        'posted_date': datetime.datetime.utcnow()
    })

    if image:
        storage_client = storage.Client()
        bucket = storage_client.bucket('ass_cloud1')
        blob = bucket.blob(f"messages/{doc_ref.id}")
        blob.upload_from_file(image)

        image_url = blob.public_url
        doc_ref.update({'image_url': image_url})

    return redirect(url_for('forum'))

# Fetch messages from the database, optionally filtering by user ID.
def fetch_messages(user_id):
    if not user_id:
        return []

    messages_query = db.collection('messages').where('user_id', '==', user_id).order_by('posted_date', direction=firestore.Query.DESCENDING).limit(10)
    messages = messages_query.stream()

    message_list = []
    for message in messages:
        message_dict = message.to_dict()
        message_dict['id'] = message.id
        message_list.append(message_dict)

    return message_list

# Display the user administration page, handling authentication and user profile updates.
@app.route('/user_admin', methods=['GET', 'POST'])
def user_admin():
    messages = []
    if 'username' not in session:
        return redirect(url_for('login'))

    user_ref = db.collection('users').document(session.get('user_id'))
    user_doc = user_ref.get()

    if request.method == 'POST':
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)
            if file:
                filename = secure_filename(file.filename)
                image_url = upload_to_cloud_storage(file, filename)

                user_ref.update({'profile_image_url': image_url})
                flash('Profile picture updated successfully!', 'success')
                return redirect(url_for('user_admin'))
        elif 'old_password' in request.form and 'new_password' in request.form:
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            user_data = user_doc.to_dict()
            if user_data['password'] == old_password:
                user_ref.update({'password': new_password})
                flash('Password updated successfully!', 'success')
                return redirect(url_for('login'))
            else:
                flash('The old password is incorrect', 'error')

    messages = fetch_messages()

    return render_template(
        'user_admin.html',
        username=session.get('username', 'Guest'),
        profile_image_url=session.get('profile_image_url', url_for('static', filename='default_profile.png')),
        messages=messages
    )

#Handles the update of the file to cloud storage
def upload_to_cloud_storage(file, filename):
    storage_client = storage.Client()
    bucket = storage_client.bucket('ass_cloud1')
    blob = bucket.blob(f"user_images/{filename}")
    blob.upload_from_file(file, content_type=file.content_type)
    blob.make_public()
    return blob.public_url

#Allows users to edit the forum message, including updating the message and attached images
@app.route('/edit-message/<message_id>', methods=['GET', 'POST'])
def edit_message(message_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    message_ref = db.collection('messages').document(message_id)
    message = message_ref.get()
    if not message.exists:
        flash('Message not found.', 'error')
        return redirect(url_for('forum'))
    message_data = message.to_dict()

    if request.method == 'POST':
        subject = request.form.get('subject')
        message_text = request.form.get('message_text')
        image = request.files.get('image')

        update_data = {
            'subject': subject,
            'message_text': message_text,
            'posted_date': datetime.datetime.now(datetime.timezone.utc)  # Updated to timezone-aware
        }

        if image:
            logging.info(f"Image file received: {image.filename}")  # Logging file receipt
            try:
                timestamp = time.time()
                file_extension = image.filename.rsplit('.', 1)[1].lower()
                new_filename = f"messages/{message_id}_{timestamp}.{file_extension}"
                storage_client = storage.Client()
                bucket = storage_client.bucket('ass_cloud1')
                blob = bucket.blob(new_filename)
                blob.upload_from_file(image, content_type=image.content_type)
                blob.make_public()
                new_image_url = blob.public_url
                update_data['image_url'] = new_image_url
                logging.info(f"Image successfully uploaded to Google Cloud Storage: {new_image_url}")
            except Exception as e:
                logging.error(f"Failed to upload new image: {e}")
                flash('Failed to upload new image. Please try again.', 'error')
        else:
            logging.info("No image file received in the request.")

        try:
            message_ref.update(update_data)
            flash('Message updated successfully!', 'success')
            logging.info(f"Firestore document for message {message_id} updated successfully.")
        except GoogleAPIError as e:
            flash('Failed to update the message. Please try again.', 'error')
            logging.error(f"Failed to update message {message_id}: {e}")

        return redirect(url_for('forum'))

    return render_template('edit_message.html', message=message_data)


#Retrieves the messages from the cloud to be displayed on the forum and user admin pages
def fetch_messages():
    if 'user_id' not in session:
        return []
    
    user_id = session['user_id']
    messages_query = db.collection('messages').where('user_id', '==', user_id).order_by('posted_date', direction=firestore.Query.DESCENDING).limit(10)
    messages = messages_query.stream()

    message_list = []
    for message in messages:
        message_dict = message.to_dict()
        message_dict['id'] = message.id
        message_list.append(message_dict)

    return message_list

#Handles the registration of a new user and stores their details in the cloud 
def perform_register(user_id, username, password, image_url, db):
    users_ref = db.collection('users')
    query = users_ref.where('id', '==', user_id)
    id_results = query.stream()
    
    for _ in id_results:
        return {"success": False, "message": "The ID already exists."}
    
    username_query = users_ref.where('username', '==', username)
    username_results = username_query.stream()

    for _ in username_results:
        return {"success": False, "message": "The username already exists."}
    
    new_user_ref = users_ref.document(user_id)
    new_user_ref.set({
        'id': user_id,
        'username': username,
        'password': password,
        'profile_image_url': image_url  
    })
    
    return {"success": True, "message": "Registration successful! Please log in."}

#Handles the user logging out of the program 
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#Starts the Flask web application by calling the run method on the app object.
if __name__ == '__main__':
    app.run(debug=True, port=5001)
