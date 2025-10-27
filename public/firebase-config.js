// Firebase Configuration
// IMPORTANTE: Substitua com suas configurações reais do Firebase Console
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Initialize Firebase services
const db = firebase.firestore();
const auth = firebase.auth();
const functions = firebase.functions();

// For local development, uncomment these lines to use emulators:
// if (window.location.hostname === "localhost") {
//     db.useEmulator("localhost", 8080);
//     functions.useEmulator("localhost", 5001);
//     auth.useEmulator("http://localhost:9099");
// }

// Helper function to generate session ID for guest users
function generateSessionId() {
    return 'guest_' + Math.random().toString(36).substring(2, 15) +
           Math.random().toString(36).substring(2, 15);
}

// Get or create session ID for guest users
function getSessionId() {
    let sessionId = localStorage.getItem('enigma_hunter_session_id');
    if (!sessionId) {
        sessionId = generateSessionId();
        localStorage.setItem('enigma_hunter_session_id', sessionId);
    }
    return sessionId;
}

// Export for use in other files
window.firebaseServices = {
    db,
    auth,
    functions,
    getSessionId,
    generateSessionId
};

console.log('Firebase initialized successfully');
