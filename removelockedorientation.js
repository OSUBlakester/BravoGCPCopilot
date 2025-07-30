// Remove lockedOrientation from all user settings documents in Firestore
const admin = require('firebase-admin');
admin.initializeApp();

const db = admin.firestore();

async function removeLockedOrientation() {
  const usersRef = db.collection('users'); // Change to your actual collection name
  const snapshot = await usersRef.get();
  let count = 0;
  for (const doc of snapshot.docs) {
    if (doc.get('lockedOrientation') !== undefined) {
      await doc.ref.update({ lockedOrientation: admin.firestore.FieldValue.delete() });
      count++;
    }
  }
  console.log(`Removed lockedOrientation from ${count} documents.`);
}

removeLockedOrientation().then(() => process.exit());