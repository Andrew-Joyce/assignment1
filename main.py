from flask import Flask, session, redirect, url_for, render_template, request, flash
from google.cloud import firestore, storage
import datetime
from register import perform_register

app = Flask(__name__)
app.secret_key = "95871372a"

db = firestore.Client()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id']
        password = request.form['password']
        
        users_ref = db.collection('user')
        query = users_ref.where('id', '==', user_id)
        results = query.stream()
        
        user = next(results, None)
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
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    profile_image_url = session.get('profile_image_url', url_for('static', filename='default_profile.png'))

    messages = fetch_user_messages(session['user_id'])

    return render_template('forum.html', user_name=session.get('user_name', 'Guest'), profile_image_url=profile_image_url, messages=messages)


@app.route('/post-message', methods=['POST'])
def post_message():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    
    subject = request.form.get('subject', '')
    message_text = request.form.get('message', '')
    image = request.files.get('image') 

    doc_ref = db.collection('messages').document()
    doc_ref.set({
        'user_id': session['user_id'], 
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

@app.route('/user_admin', methods=['GET', 'POST'])
def user_admin():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        user_ref = db.collection('user').document(session['user_id'])
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            if user_data['password'] == old_password:
                user_ref.update({'password': new_password})
                flash('Password updated successfully!', 'success')
                return redirect(url_for('login'))
            else:
                flash('The old password is incorrect', 'error')
        else:
            flash('No user found with this ID.', 'error')

        messages = fetch_user_messages(session['user_id'])
        return render_template('user_admin.html', user_name=session.get('user_name', 'Guest'), profile_image_url=session.get('profile_image_url', url_for('static', filename='default_profile.png')), messages=messages)
    
    messages = fetch_user_messages(session.get('user_id', ''))
    return render_template('user_admin.html', user_name=session.get('user_name', 'Guest'), profile_image_url=session.get('profile_image_url', url_for('static', filename='default_profile.png')), messages=messages)


@app.route('/edit-message/<message_id>', methods=['GET', 'POST'])
def edit_message(message_id):
    if 'user_name' not in session:
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
            'posted_date': datetime.datetime.utcnow()
        }

        if image:
            storage_client = storage.Client()
            bucket = storage_client.bucket('ass_cloud1')
            blob = bucket.blob(f"messages/{message_id}")
            blob.upload_from_file(image, content_type=image.content_type)
            blob.make_public()
            update_data['image_url'] = blob.public_url

        message_ref.update(update_data)
        flash('Message updated successfully!', 'success')
        return redirect(url_for('forum'))

    return render_template('edit_message.html', message=message_data)


def fetch_user_messages(user_id):
    messages_query = db.collection('messages').where('user_id', '==', user_id).order_by('posted_date', direction=firestore.Query.DESCENDING)
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
