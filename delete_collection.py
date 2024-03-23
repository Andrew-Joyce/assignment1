from google.cloud import firestore

db = firestore.Client()

def delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f'Deleting document {doc.id} => {doc.to_dict()}')
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

# Delete messages collection
messages_ref = db.collection('messages')
print('Deleting messages collection...')
delete_collection(messages_ref, batch_size=10)

# Delete user collection
users_ref = db.collection('user')
print('Deleting user collection...')
delete_collection(users_ref, batch_size=10)

# Delete users collection
users_ref = db.collection('users')
print('Deleting users collection...')
delete_collection(users_ref, batch_size=10)

print('Data deletion completed successfully.')
