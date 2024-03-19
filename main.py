from flask import Flask, session, redirect, url_for, render_template, request, flash
from google.cloud import firestore, storage
import datetime
from register import perform_register

app = Flask(__name__)
app.secret_key = "95871372a"

# Initialize Firestore client
db = firestore.Client()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id']
        password = request.form['password']
        
        # Query Firestore for user with matching 'id'
        users_ref = db.collection('user')
        query = users_ref.where('id', '==', user_id)
        results = query.stream()
        
        user = next(results, None)  # Get the first result
        if user:
            user_data = user.to_dict()
            if user_data.get('password') == password:  
                session['user_id'] = user_id
                session['user_name'] = user_data.get('username')
                session['profile_image_url'] = user_data.get('profile_image_url')  
                return redirect(url_for('forum'))
        
        flash('ID or password is invalid', 'error')
        return render_template('login.html')
    else:
        return render_template('login.html')

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

@app.route('/forum')
def forum():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    user_name = session['user_name']
    profile_image_url = session.get('profile_image_url', '')
    messages = fetch_messages()
    return render_template('forum.html', user_name=user_name, profile_image_url=profile_image_url, messages=messages)

@app.route('/post-message', methods=['POST'])
def post_message():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    
    subject = request.form.get('subject', '')
    message_text = request.form.get('message', '')
    image = request.files.get('image') 

    doc_ref = db.collection('messages').document()
    doc_ref.set({
        'user_name': session['user_name'],
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


def fetch_messages():
    messages_query = db.collection('messages').order_by('posted_date', direction=firestore.Query.DESCENDING).limit(10)
    messages = messages_query.stream()

    message_list = []
    for message in messages:
        message_dict = message.to_dict()
        message_dict['id'] = message.id
        message_list.append(message_dict)

    return message_list

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
