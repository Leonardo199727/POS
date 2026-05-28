# Point of Sale (POS) System

Welcome to the **POS System** repository. This is a comprehensive, full-stack Point of Sale application designed to manage sales, inventory, customers, and business operations seamlessly. 

The project is structured with a distinct backend API and a modern frontend web application, along with a desktop application wrapper.

## 🌟 Key Features

- **Sales Management**: Process transactions, manage carts, and generate receipts.
- **Inventory Tracking**: Real-time stock updates, product categorization, and low-stock alerts.
- **Customer Management**: Maintain customer profiles, track purchase history, and manage store credit or layaways.
- **Role-Based Access Control (RBAC)**: Secure access management with custom roles (Admin, Cashier, Manager, etc.) and fine-grained permissions.
- **Cash Management**: Manage cash registers, daily openings, closings, and cash flow tracking.
- **Reporting & Analytics**: Generate detailed PDF and Excel reports for sales, inventory, and financial statements.
- **Cross-Platform**: Accessible via a web browser or through the dedicated desktop application.

## 🏗️ System Architecture

The POS system is built using a modern, decoupled architecture:

### 1. Backend API (`/backend`)
A robust RESTful API built with **Django** (Python).
- **Apps**: Modularized into specialized Django apps including `accounts`, `sales`, `inventory`, `customers`, `cash`, `payments`, `products`, `security`, and `reports`.
- **Database**: Configured to use SQLite (for development) or PostgreSQL (for production).
- **Authentication**: Token-based authentication securing API endpoints.

### 2. Frontend Application (`/frontend`)
A highly responsive and interactive single-page application (SPA).
- **Tech Stack**: React 19, TypeScript, and Vite.
- **Styling**: Tailwind CSS for a modern, responsive UI.
- **Routing**: React Router DOM.
- **Data Fetching**: Axios for API communication.
- **Utilities**: `jspdf` and `xlsx-js-style` for client-side report generation.

### 3. Desktop Application (`/Desktop`)
A desktop wrapper enabling native-like experience and potential hardware integrations (e.g., receipt printers, barcode scanners).

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- pip & virtualenv

### Setting up the Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run database migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the Django development server:
   ```bash
   python manage.py runserver
   ```
   *The API will be available at `http://localhost:8000`.*

### Setting up the Frontend
1. Open a new terminal window and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node.js dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The web application will be available at `http://localhost:5173`.*

## 📚 Documentation
For detailed information about the database schema, API endpoints, and module architecture, please refer to the documents inside `backend/DOCUMENTACION/`.

## 🔒 Security
This application implements strict security measures, including token authentication and a comprehensive RBAC system. Always ensure you are testing with appropriate user roles and that sensitive environment variables are kept secure.
