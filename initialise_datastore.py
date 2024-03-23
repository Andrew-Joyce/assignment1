from google.cloud import firestore

db = firestore.Client()

def create_user_entities_firestore():
    for i in range(10):
        user_id = f's3876520{i}'
        password = ''.join(str((j + i) % 10) for j in range(6))
        username = f'AndrewJoyce{i}'
        document_reference = db.collection('users').document(user_id)
        document_reference.set({
            'id': user_id,
            'username': username, 
            'password': password
        })

create_user_entities_firestore()



