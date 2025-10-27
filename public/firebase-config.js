// Firebase Configuration
// Este arquivo aguarda o Firebase SDK carregar antes de inicializar

(function() {
    'use strict';

    // Aguardar o Firebase carregar
    function initFirebase() {
        // Verificar se Firebase está disponível
        if (typeof firebase === 'undefined') {
            console.error('Firebase SDK not loaded. Make sure Firebase scripts are loaded before this file.');
            return;
        }

        // Configuração do Firebase
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
        try {
            firebase.initializeApp(firebaseConfig);
            console.log('✓ Firebase initialized successfully');
        } catch (error) {
            console.error('Error initializing Firebase:', error);
            return;
        }

        // Initialize Firebase services
        const db = firebase.firestore();
        const auth = firebase.auth();
        const functions = firebase.functions();

        // For local development with emulators
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            console.log('🔧 Using Firebase Emulators');
            db.useEmulator("localhost", 8080);
            functions.useEmulator("localhost", 5001);
            auth.useEmulator("http://localhost:9099");
        }

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
            db: db,
            auth: auth,
            functions: functions,
            getSessionId: getSessionId,
            generateSessionId: generateSessionId
        };

        console.log('✓ Firebase services ready');
    }

    // Executar quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFirebase);
    } else {
        initFirebase();
    }
})();
