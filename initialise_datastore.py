from google.cloud import firestore

db = firestore.Client()

def create_user_entities_firestore():
    for i in range(10):
        document_reference = db.collection('users').document(f's3876520{i}')
        document_reference.set({
            'id': f's3876520{i}',
            'user_name': f'Andrew Joyce{i}',
            'password': f'{i}{i+1}{i+2}{i+3}{i+4}{i+5}'
        })

create_user_entities_firestore()

