import React from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';

// --- Your Page Imports ---
import './index.css';
import App from './App';
import DebugPage from './DebugPage';

// 1. Define all your application routes
const router = createBrowserRouter([
    {
        path: "/",
        element: <App />, // App handles auth for the root path
    },
    {
        path: "/debug",
        element: <DebugPage />,
    },
    // ... add other routes here
]);

// 2. Get the root element
const rootElement = document.getElementById('root')!;
const root = createRoot(rootElement);

// 3. Render the app *once* using the RouterProvider
root.render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);