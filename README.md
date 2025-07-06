# AI-Driven Genetic Disorder Detection API

A comprehensive FastAPI-based application for analyzing genetic variants and providing clinical insights using AI agents with search capabilities.

## 🚀 Features

- **VCF File Analysis**: Upload and analyze VCF files containing genetic variants
- **AI-Powered Insights**: Get detailed clinical analysis using AI agents
- **Chat Interface**: Interactive chat sessions for genetic analysis
- **Authentication**: Secure user authentication and session management
- **Sample Genotype Support**: Handle VCF files with sample genotype data
- **Comprehensive Parsing**: Support for both standard and complex VCF formats
- **Real-time Search**: Integration with medical databases and scientific literature

## 📋 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Frontend Integration](#frontend-integration)
- [VCF File Format](#vcf-file-format)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## 🛠️ Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- Google Gemini API key
- Tavily API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-driven-genetic-disorder-detection
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file:
   ```env
   # Database
   DATABASE_URL=postgresql://username:password@localhost:5432/genetic_db
   
   # API Keys
   GEMINI_API_KEY=your_gemini_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   
   # JWT Secret
   SECRET_KEY=your_secret_key_here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

4. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb genetic_db
   
   # Run migrations (tables will be created automatically on startup)
   ```

5. **Start the application**
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `GEMINI_API_KEY` | Google Gemini API key | Yes | - |
| `TAVILY_API_KEY` | Tavily search API key | Yes | - |
| `SECRET_KEY` | JWT secret key | Yes | - |
| `ALGORITHM` | JWT algorithm | No | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | No | 30 |

### Production Settings

For production deployment, consider:

1. **Database**: Use a managed PostgreSQL service
2. **CORS**: Configure `allow_origins` with specific domains
3. **Logging**: Set up proper log aggregation
4. **File Storage**: Use cloud storage for VCF files
5. **Rate Limiting**: Implement API rate limiting

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Authentication

Most endpoints require authentication. Use JWT tokens:

1. **Register**: `POST /auth/register`
2. **Login**: `POST /auth/login`
3. **Include token**: `Authorization: Bearer <your_token>`

### Core Endpoints

#### Health Check
```http
GET /
GET /health
```

#### Authentication
```http
POST /auth/register
POST /auth/login
```

#### Chat Interface
```http
POST /chat
```

#### Chat Management
```http
GET /chats
GET /chats/{chat_id}
DELETE /chats/{chat_id}
```

#### Direct Analysis
```http
POST /analyze
```

## 🎨 Frontend Integration

### React/Next.js Example

```typescript
// types.ts
interface ChatResponse {
  session_id: string;
  response: string;
  chat_history: Array<{
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
  }>;
  chat_title: string;
}

interface VariantInfo {
  chromosome: string;
  position: number;
  rsid: string;
  gene: string;
  reference: string;
  alternate: string;
  search_summary: string;
}

// api.ts
const API_BASE = 'http://localhost:8000';

class GeneticAPI {
  private token: string;

  constructor(token: string) {
    this.token = token;
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Chat with text message
  async chatWithText(sessionId: string | null, message: string): Promise<ChatResponse> {
    const formData = new FormData();
    if (sessionId) formData.append('session_id', sessionId);
    formData.append('message', message);

    return this.request('/chat', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    });
  }

  // Chat with VCF file
  async chatWithFile(sessionId: string | null, file: File): Promise<ChatResponse> {
    const formData = new FormData();
    if (sessionId) formData.append('session_id', sessionId);
    formData.append('file', file);

    return this.request('/chat', {
      method: 'POST',
      body: formData,
      headers: {},
    });
  }

  // Direct VCF analysis
  async analyzeVCF(file: File): Promise<{
    message: string;
    chat_id: string;
    variants_analyzed: number;
    results: VariantInfo[];
  }> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request('/analyze', {
      method: 'POST',
      body: formData,
      headers: {},
    });
  }

  // Get chat history
  async getChats(): Promise<Array<{
    id: string;
    title: string;
    created_at: string;
  }>> {
    return this.request('/chats');
  }

  // Get specific chat
  async getChat(chatId: string): Promise<{
    id: string;
    title: string;
    messages: Array<{
      role: 'user' | 'assistant';
      content: string;
      created_at: string;
    }>;
  }> {
    return this.request(`/chats/${chatId}`);
  }
}

// React component example
import React, { useState, useRef } from 'react';

const GeneticAnalysis: React.FC = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([]);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const api = new GeneticAPI('your-jwt-token');

  const sendMessage = async (message: string) => {
    setLoading(true);
    try {
      const response = await api.chatWithText(sessionId, message);
      setSessionId(response.session_id);
      setMessages(response.chat_history);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const uploadFile = async (file: File) => {
    setLoading(true);
    try {
      const response = await api.chatWithFile(sessionId, file);
      setSessionId(response.session_id);
      setMessages(response.chat_history);
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="genetic-analysis">
      <div className="chat-container">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="content">{msg.content}</div>
          </div>
        ))}
      </div>
      
      <div className="input-container">
        <input
          type="file"
          ref={fileInputRef}
          accept=".vcf,.vcf.gz"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadFile(file);
          }}
        />
        <button onClick={() => fileInputRef.current?.click()}>
          Upload VCF
        </button>
      </div>
      
      {loading && <div className="loading">Analyzing...</div>}
    </div>
  );
};
```

### Vue.js Example

```vue
<template>
  <div class="genetic-analysis">
    <div class="chat-container">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.role]"
      >
        <div class="content">{{ message.content }}</div>
      </div>
    </div>
    
    <div class="input-container">
      <input
        ref="fileInput"
        type="file"
        accept=".vcf,.vcf.gz"
        @change="handleFileUpload"
        style="display: none"
      />
      <button @click="$refs.fileInput.click()">Upload VCF</button>
    </div>
    
    <div v-if="loading" class="loading">Analyzing...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';

const sessionId = ref<string | null>(null);
const messages = ref<Array<{role: string, content: string}>>([]);
const loading = ref(false);
const fileInput = ref<HTMLInputElement>();

const api = new GeneticAPI('your-jwt-token');

const handleFileUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  
  loading.value = true;
  try {
    const response = await api.chatWithFile(sessionId.value, file);
    sessionId.value = response.session_id;
    messages.value = response.chat_history;
  } catch (error) {
    console.error('Error uploading file:', error);
  } finally {
    loading.value = false;
  }
};
</script>
```

## 📄 VCF File Format

### Standard VCF Format

```vcf
##fileformat=VCFv4.2
##source=Example
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene name">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE1	SAMPLE2
1	1234567	rs123456	A	G	.	PASS	GENE=BRCA1	GT	0/0	0/1
2	7654321	rs987654	C	T	.	PASS	GENE=TP53	GT	0/1	1/1
```

### Supported Features

- **Standard VCF fields**: CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO
- **Sample genotype data**: FORMAT and sample columns
- **Gene information**: Extracted from INFO field (GENE=...)
- **Multiple separators**: Tab and space-separated files
- **File compression**: .vcf and .vcf.gz files

### File Size Limits

- **Maximum file size**: 10MB
- **Recommended**: < 5MB for optimal performance

## 🔧 Development

### Project Structure

```
ai-driven-genetic-disorder-detection/
├── main.py                 # FastAPI application entry point
├── utils.py               # VCF parsing and AI agent utilities
├── custom_types.py        # Pydantic models
├── app/
│   ├── models.py          # SQLAlchemy database models
│   ├── database.py        # Database configuration
│   ├── schemas.py         # Pydantic schemas
│   └── routers/
│       ├── auth.py        # Authentication endpoints
│       ├── chat.py        # Chat management
│       └── message.py     # Message handling
├── tools/
│   ├── google_search_tool.py
│   └── tavily_search_tool.py
├── uploads/               # VCF file storage
└── tests/                 # Test files
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Code Quality

```bash
# Install linting tools
pip install black flake8 mypy

# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t genetic-api .
docker run -p 8000:8000 genetic-api
```

### Production Deployment

1. **Use a production WSGI server**:
   ```bash
   pip install gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. **Set up reverse proxy** (nginx):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Environment variables**:
   ```bash
   export DATABASE_URL="postgresql://..."
   export GEMINI_API_KEY="your-key"
   export TAVILY_API_KEY="your-key"
   export SECRET_KEY="your-secret"
   ```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```
   Error: Failed to create database tables
   ```
   **Solution**: Check DATABASE_URL and ensure PostgreSQL is running

2. **API Key Errors**
   ```
   Error: GEMINI_API_KEY environment variable is required
   ```
   **Solution**: Set all required environment variables

3. **VCF Parsing Issues**
   ```
   Error: No valid variants found in VCF file
   ```
   **Solution**: Check VCF file format and ensure it's tab-separated

4. **File Upload Errors**
   ```
   Error: File size must be less than 10MB
   ```
   **Solution**: Compress large VCF files or split them

### Logs

Check application logs:
```bash
tail -f app.log
```

### Health Check

Monitor application health:
```bash
curl http://localhost:8000/health
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions:
- Email: ma2404374@gmail.com
- GitHub Issues: [Create an issue](https://github.com/your-repo/issues)

## 🔄 Changelog

### Version 1.0.0
- Initial release
- VCF file parsing and analysis
- AI-powered genetic insights
- Chat interface
- Authentication system
- Sample genotype support
