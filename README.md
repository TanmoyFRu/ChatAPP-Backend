#  FastAPI Chat API with AI Integration

A modern, scalable chat API built with FastAPI that integrates Google Gemini AI to provide intelligent responses to user messages. The system features real-time messaging, JWT authentication, room-based conversations, and asynchronous AI processing.

##  Features

- ** JWT Authentication** - Secure user registration and login
- ** Room Management** - Create and manage chat rooms
- ** Real-time Messaging** - Send messages and get instant AI responses
- ** AI Integration** - Google Gemini AI provides immediate intelligent responses
- ** Async Processing** - Celery task queue for non-blocking AI responses
- ** Auto Documentation** - Interactive API docs with Swagger UI
- ** Type Safety** - Pydantic models with full validation
- ** CORS Support** - Ready for frontend integration
- ** Message History** - Paginated message retrieval with conversation context

##  Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | FastAPI |
| **Database** | SQLAlchemy (SQLite/PostgreSQL) |
| **Authentication** | JWT (JSON Web Tokens) |
| **Task Queue** | Celery + Redis |
| **AI Integration** | Google Gemini API |
| **Documentation** | Automatic OpenAPI/Swagger |
| **Validation** | Pydantic v2 |

##  Project Structure

```
chat_api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app and routes setup
│   ├── models.py              # SQLAlchemy database models
│   ├── schemas.py             # Pydantic request/response models
│   ├── database.py            # Database connection and session
│   ├── auth.py                # JWT authentication dependency
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Application configuration
│   │   └── security.py        # Password hashing and JWT utils
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── rooms.py           # Room management endpoints
│   │   └── chat.py            # Messaging endpoints
│   └── services/
│       ├── __init__.py
│       ├── gemini_client.py   # Google Gemini AI client
│       └── tasks.py           # Celery background tasks
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables
└── README.md                 # This file
```

##  Quick Start

### Prerequisites

- Python 3.8+
- Redis Server
- Google Gemini API Key

### 1. Installation

```bash
# Clone the repository
git clone <https://github.com/TanmoyFRu/ChatAPP-Backend/blob/main>
cd chat_api

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the root directory:

```env
# App Configuration
APP_NAME=Chat API
DEBUG=true

# Database
DATABASE_URL=sqlite:///./chat.db

# Security
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Gemini API
GEMINI_API_KEY=your-gemini-api-key-here

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Redis Setup

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download and install from [Redis Official Website](https://redis.io/download)

### 4. Run the Application

**Terminal 1 - FastAPI Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
celery -A app.services.tasks.celery_app worker --loglevel=info
```

### 5. Access the API

- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

##  API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register a new user |
| POST | `/auth/login` | Login and get JWT token |
| GET | `/auth/me` | Get current user info |

### Room Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/rooms/` | Create a new chat room |
| GET | `/rooms/` | Get all rooms |
| GET | `/rooms/{room_id}` | Get room with last 10 messages |

### Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/{room_id}` | Send message (gets instant AI response) |

##  How AI Integration Works

1. **User sends message** → Message saved to database immediately
2. **AI processes request** → Gemini analyzes message + conversation history  
3. **AI response generated** → AI response saved to database
4. **Both messages returned** → Single API call returns user message + AI response
5. **Real-time experience** → Instant AI responses in the same request

### AI Features:
- **Context Awareness** - Uses conversation history for better responses
- **Instant Responses** - AI reply included in the same API response
- **Conversation History** - Maintains chat flow understanding
- **Error Handling** - Graceful fallback for API failures
- **Synchronous Processing** - Fast, real-time user experience

##  API Usage Examples

### 1. User Registration

```bash
curl -X POST "http://localhost:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com", 
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "message": "User created successfully",
  "data": {
    "user": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "username": "john_doe",
      "email": "john@example.com",
      "created_at": "2024-01-15T10:30:00"
    }
  }
}
```

### 2. User Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

### 3. Create Chat Room

```bash
curl -X POST "http://localhost:8000/rooms/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "General Discussion",
    "description": "A place for general conversations"
  }'
```

**Response:**
```json
{
  "message": "Room created successfully",
  "data": {
    "room": {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "name": "General Discussion",
      "description": "A place for general conversations",
      "created_by": "123e4567-e89b-12d3-a456-426614174000",
      "created_at": "2024-01-15T10:35:00",
      "message_count": 0
    }
  }
}
```

### 4. Send Message (AI Integration)

```bash
curl -X POST "http://localhost:8000/chat/456e7890-e89b-12d3-a456-426614174001" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "content": "Hello! Can you explain quantum computing?"
  }'
```

**Response:**
```json
{
  "message": "Messages sent successfully",
  "data": {
    "messages": {
      "user_message": {
        "id": "789e0123-e89b-12d3-a456-426614174002",
        "m_id": "msg_789e0123-unique-id",
        "content": "Hello! Can you explain quantum computing?",
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "room_id": "456e7890-e89b-12d3-a456-426614174001",
        "message_type": "user",
        "username": "john_doe",
        "created_at": "2024-01-15T10:40:00"
      },
      "ai_message": {
        "id": "890e1234-e89b-12d3-a456-426614174003",
        "m_id": "ai_890e1234-unique-id", 
        "content": "Quantum computing is a revolutionary computing paradigm that harnesses quantum mechanics principles like superposition and entanglement to process information in ways classical computers cannot. Unlike classical bits that exist in either 0 or 1 states, quantum bits (qubits) can exist in multiple states simultaneously through superposition, allowing quantum computers to perform many calculations at once...",
        "user_id": null,
        "room_id": "456e7890-e89b-12d3-a456-426614174001",
        "message_type": "ai",
        "username": "AI Assistant",
        "created_at": "2024-01-15T10:40:01"
      }
    }
  }
}
```

### 5. Get Room with Messages

```bash
curl -X GET "http://localhost:8000/rooms/456e7890-e89b-12d3-a456-426614174001" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "name": "General Discussion",
  "description": "A place for general conversations",
  "created_by": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2024-01-15T10:35:00",
  "message_count": 2,
  "messages": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174002",
      "m_id": "msg_789e0123-unique-id",
      "content": "Hello! Can you explain quantum computing?",
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "room_id": "456e7890-e89b-12d3-a456-426614174001",
      "message_type": "user",
      "username": "john_doe",
      "created_at": "2024-01-15T10:40:00"
    },
    {
      "id": "890e1234-e89b-12d3-a456-426614174003",
      "m_id": "ai_890e1234-unique-id", 
      "content": "Quantum computing is a revolutionary computing paradigm that harnesses quantum mechanics...",
      "user_id": null,
      "room_id": "456e7890-e89b-12d3-a456-426614174001",
      "message_type": "ai",
      "username": "AI Assistant",
      "created_at": "2024-01-15T10:40:15"
    }
  ]
}
```

##  Database Schema

### Users Table
```sql
- id (String, Primary Key)
- username (String, Unique)
- email (String, Unique) 
- password_hash (String)
- created_at (DateTime)
```

### Rooms Table
```sql
- id (String, Primary Key)
- name (String)
- description (Text)
- created_by (String, Foreign Key → users.id)
- created_at (DateTime)
```

### Messages Table
```sql
- id (String, Primary Key)
- m_id (String, Unique) # Your custom message ID
- content (Text)
- user_id (String, Foreign Key → users.id, Nullable for AI)
- room_id (String, Foreign Key → rooms.id)
- message_type (String: 'user' | 'ai')
- created_at (DateTime)
```

##  Real-World Test Results

Based on your test output, here's what happens when you send a message:

**Input Message:**
```json
{
  "content": "Hello AI, how are you?"
}
```

**API Response (Both Messages Instantly):**
```json
{
  "message": "Messages sent successfully",
  "data": {
    "messages": {
      "user_message": {
        "id": "8de027ee-28cb-4de6-b228-7bb19414b5a2",
        "m_id": "258831f7-1d89-4072-a382-cd3a6439a53b",
        "content": "Hello AI, how are you?",
        "user_id": "9f3dfe25-6b50-4fc9-9b47-6edb01031e74",
        "room_id": "9705e8f5-96c2-4915-be21-745128f0a9e5",
        "message_type": "user",
        "username": "testuser_27735",
        "created_at": "2025-08-10T12:07:24"
      },
      "ai_message": {
        "id": "885e2c46-9e29-400e-8dae-0fa55519ea73",
        "m_id": "35d961e2-76a2-49ba-bebc-e33b5435c7bb",
        "content": "Hello! I'm doing well, thank you for asking. How can I help you today?",
        "user_id": null,
        "room_id": "9705e8f5-96c2-4915-be21-745128f0a9e5",
        "message_type": "ai",
        "username": "AI Assistant",
        "created_at": "2025-08-10T12:07:24"
      }
    }
  }
}
```

##  Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | "Chat API" |
| `DEBUG` | Debug mode | true |
| `DATABASE_URL` | Database connection string | "sqlite:///./chat.db" |
| `SECRET_KEY` | JWT secret key | *Required* |
| `GEMINI_API_KEY` | Google Gemini API key | *Required* |
| `REDIS_URL` | Redis connection string | "redis://localhost:6379/0" |

### Database Options

**SQLite (Development):**
```env
DATABASE_URL=sqlite:///./chat.db
```

**PostgreSQL (Production):**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/chatdb
```

##  Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Test AI Response
1. Create a user account
2. Create a room  
3. Send a message
4. Get instant AI response in the same API call
5. Optionally fetch the room messages to see full conversation history

##  Security Features

- **JWT Authentication** - Secure token-based auth
- **Password Hashing** - BCrypt password encryption
- **CORS Protection** - Configurable cross-origin requests
- **Input Validation** - Pydantic model validation
- **SQL Injection Protection** - SQLAlchemy ORM protection

##  Scalability

- **Async Processing** - Celery for background tasks
- **Database Agnostic** - SQLAlchemy supports multiple databases
- **Horizontal Scaling** - Stateless API design
- **Caching Ready** - Redis integration for future caching
- **Load Balancer Friendly** - No server-side sessions

##  Troubleshooting

### Common Issues

**1. ModuleNotFoundError: No module named 'pydantic_settings'**
```bash
pip install pydantic-settings
```

**2. Redis Connection Error**
```bash
# Check if Redis is running
redis-cli ping
# Should return "PONG"
```

**3. Gemini API Error**
- Verify your API key is correct
- Check API quotas and limits
- Ensure internet connectivity

**4. Database Connection Error**
```bash
# For SQLite, ensure write permissions
chmod 777 .
# For PostgreSQL, check connection string
```

### Debug Mode

Enable detailed logging:
```bash
export DEBUG=true
uvicorn app.main:app --reload --log-level debug
```

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Acknowledgments

- **FastAPI** - Modern, fast web framework
- **Google Gemini** - AI integration
- **Celery** - Distributed task queue
- **SQLAlchemy** - SQL toolkit and ORM
- **Pydantic** - Data validation using Python type hints

---

##  Support

For support, email tanmoydn2003@example.com or create an issue in the repository.
