// Firebase Configuration - Ambiente Development
// Este arquivo usa variáveis de ambiente para segurança

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
        // IMPORTANTE: Para desenvolvimento local, use as configurações de emulador
        // Para produção, substitua com suas configurações reais do Firebase Console

        let firebaseConfig;

        // Detectar ambiente
        const isLocalhost = window.location.hostname === 'localhost' ||
                           window.location.hostname === '127.0.0.1';

        if (isLocalhost) {
            // Configuração para emuladores (desenvolvimento)
            console.log('🔧 Modo: Desenvolvimento (Emulators)');
            firebaseConfig = {
                apiKey: "demo-api-key",
                authDomain: "demo-project.firebaseapp.com",
                projectId: "demo-project",
                storageBucket: "demo-project.appspot.com",
                messagingSenderId: "123456789",
                appId: "1:123456789:web:abcdef"
            };
        } else {
            // Configuração para produção
            // SUBSTITUA com suas credenciais reais do Firebase Console
            console.log('🚀 Modo: Produção');
            firebaseConfig = {
                apiKey: import.meta.env.VITE_API_KEY || "YOUR_API_KEY",
                authDomain: import.meta.env.VITE_AUTH_DOMAIN || "YOUR_PROJECT_ID.firebaseapp.com",
                projectId: import.meta.env.VITE_PROJECT_ID || "YOUR_PROJECT_ID",
                storageBucket: import.meta.env.VITE_STORAGE_BUCKET || "YOUR_PROJECT_ID.appspot.com",
                messagingSenderId: window.ENV?.FIREBASE_MESSAGING_SENDER_ID || "YOUR_MESSAGING_SENDER_ID",
                appId: window.ENV?.FIREBASE_APP_ID || "YOUR_APP_ID"
            };
        }

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

        // Configurar emuladores para localhost
        if (isLocalhost) {
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