# Imports the firestore module from the google.cloud package.
from google.cloud import firestore

# Create a Firestore client instance to interact with the Firestore database.
db = firestore.Client()

# Defines a function named create_user_entities_firestore to create user entities in Firestore.
def create_user_entities_firestore():
    # Iterates through a range of 10, generating user entities.
    for i in range(10):
        # Generate a user ID using the format s3876520{i}
        user_id = f's3876520{i}'
        # Generates a password by concatenating digits from 0 to 5, cyclically shifted by the current index i.
        password = ''.join(str((j + i) % 10) for j in range(6))
        # Generates a username using the format AndrewJoyce{i}.
        username = f'AndrewJoyce{i}'
        # Gets a reference to the document in the users collection with the generated user ID.
        document_reference = db.collection('users').document(user_id)
        # Sets the document data with user ID, username, and password.
        document_reference.set({
            'id': user_id,
            'username': username, 
            'password': password
        })
# Calls the function to create user entities in Firestore.
create_user_entities_firestore()



