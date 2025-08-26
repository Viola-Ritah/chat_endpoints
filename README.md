# Travel App Backend

This is the backend service for the Travel App, built with FastAPI and PostgreSQL.

## Prerequisites

- Python 3.8+
- PostgreSQL 13+
- pip (Python package manager)

## Setup

1. **Clone the repository**

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   - Create a new PostgreSQL database named `traveler_app`
   - Update the `.env` file with your database credentials

5. **Initialize the database**
   ```bash
   python init_db.py
   ```

## Running the Application

1. **Start the development server**
   ```bash
   uvicorn main:app --reload
   ```

2. **Access the API documentation**
   - Open your browser and go to: http://localhost:8000/docs

## Environment Variables

Create a `.env` file in the backend directory with the following variables:

```
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/traveler_app

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 1 week
```

## Project Structure

```
backend/
├── .env                    # Environment variables
├── requirements.txt        # Project dependencies
├── main.py                # Main application file
├── database.py            # Database configuration
├── init_db.py             # Database initialization script
├── models/                # Database models
│   ├── __init__.py
│   ├── user.py
│   └── conversation.py
└── README.md              # This file
```

## API Endpoints

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get access token
- `GET /api/users/me` - Get current user info
- `GET /api/conversations` - Get user's conversations
- `POST /api/conversations` - Create a new conversation
- `GET /api/conversations/{conversation_id}/messages` - Get messages in a conversation
- `POST /api/messages` - Send a new message

## Deployment

### Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Render account (for cloud deployment)

### Local Deployment with Docker

1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

2. The API will be available at http://localhost:8000

### Deployment to Render

1. Push your code to a GitHub repository
2. Create a new Web Service on Render and connect your repository
3. Set the following environment variables in the Render dashboard:
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `SECRET_KEY`: A secure secret key for JWT
   - `ALGORITHM`: HS256
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: 10080
4. Set the build command: `pip install -r requirements.txt`
5. Set the start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
