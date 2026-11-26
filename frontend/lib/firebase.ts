import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getDatabase, Database } from "firebase/database";

const rawDatabaseUrl = process.env.NEXT_PUBLIC_FIREBASE_DATABASE_URL || "";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "",
  ...(rawDatabaseUrl ? { databaseURL: rawDatabaseUrl } : {})
};

/**
 * True only when real Firebase web credentials are present.
 */
export const firebaseConfigured = Boolean(
  process.env.NEXT_PUBLIC_FIREBASE_API_KEY &&
    process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN &&
    process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID &&
    process.env.NEXT_PUBLIC_FIREBASE_APP_ID
);

let app = null;
let authInstance = null;
let databaseInstance: Database | null = null;

if (firebaseConfigured) {
  try {
    app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
    authInstance = getAuth(app);
    if (rawDatabaseUrl) {
      databaseInstance = getDatabase(app);
    }
  } catch (err) {
    console.warn("Firebase client initialization failed (check API keys in .env.local):", err);
  }
}

export const auth = authInstance;
export const database = databaseInstance;
export const googleProvider = new GoogleAuthProvider();



