# register.py
from google.cloud import firestore

def perform_register(user_id, username, password, image_url, db):
    users_ref = db.collection('user')
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
