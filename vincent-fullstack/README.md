# Vincent Review Queue API - v2.0.0

**Production-Grade, Security-First Backend**

> Transformed from prototype to industry-standard code with comprehensive security hardening, authentication, rate limiting, and comprehensive logging.

## Quick Start

### Development
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
curl http://localhost:5000/health
```

### Production (Docker)
```bash
cp .env.example .env.production
# Edit .env.production with production secrets
docker-compose up -d
curl http://localhost:8000/health
```

## Architecture

```
app/
├── auth/                    # JWT authentication & RBAC
│   ├── models.py           # User model with role management
│   └── routes.py           # Auth endpoints (login, register, refresh)
├── review_queue/           # Core document review logic
│   ├── models.py           # Document, Template, RiskFlag, AuditEntry
│   ├── routes.py           # Review queue endpoints
│   └── risk.py             # Risk assessment logic
├── security.py             # Auth decorators, sanitization, logging
├── schemas.py              # Pydantic validation schemas
├── config.py               # Environment-based configuration
├── extensions.py           # SQLAlchemy, Limiter initialization
└── __init__.py            # App factory with security middleware
```

## Security Features

✅ **JWT Authentication** - Secure token-based access control  
✅ **Role-Based Access Control** - Admin, Reviewer, Automation roles  
✅ **Input Validation** - Pydantic schemas on all endpoints  
✅ **XSS Prevention** - HTML escaping on all user inputs  
✅ **Rate Limiting** - IP-based throttling (customizable per endpoint)  
✅ **CORS Protection** - Configurable origins, restricted methods  
✅ **Security Headers** - HSTS, CSP, X-Frame-Options, etc.  
✅ **Audit Logging** - Complete event trail with timestamps  
✅ **Password Security** - PBKDF2-SHA256 with 16-byte salt  
✅ **Database Security** - Parameterized queries, foreign keys, cascades  
✅ **Error Handling** - Safe error responses, no information leakage  
✅ **Production Deployment** - Gunicorn, Docker, non-root user  

## Authentication

### Register
```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "reviewer1",
    "email": "reviewer@example.com",
    "password": "SecurePass123",
    "roles": ["reviewer"]
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "reviewer1", "password": "SecurePass123"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Use Token
```bash
curl -X GET http://localhost:5000/api/queue \
  -H "Authorization: Bearer <access_token>"
```

## API Endpoints

### Authentication (Public)
- `POST /auth/register` - Create new user account
- `POST /auth/login` - Authenticate and get tokens
- `POST /auth/refresh` - Refresh expired access token

### Current User (Protected)
- `GET /auth/me` - Get current authenticated user

### Admin (Admin Only)
- `GET /auth/users` - List all users
- `GET /auth/users/<user_id>` - Get specific user
- `POST /auth/users/<user_id>/activate` - Activate user
- `POST /auth/users/<user_id>/deactivate` - Deactivate user

### Review Queue (Authenticated)
- `GET /api/queue` - List documents (paginated, sortable)
- `POST /api/queue` - Create document
- `GET /api/queue/<doc_id>` - Get document details
- `PATCH /api/queue/<doc_id>` - Update pending document
- `POST /api/queue/<doc_id>/approve` - Approve document (Reviewer/Admin)
- `POST /api/queue/<doc_id>/reject` - Reject document (Reviewer/Admin)
- `POST /api/queue/bulk-approve` - Bulk approval (Reviewer/Admin)

### Templates (Authenticated)
- `GET /api/templates` - List all templates
- `POST /api/templates` - Create template
- `GET /api/templates/<template_id>` - Get template
- `DELETE /api/templates/<template_id>` - Delete template
- `POST /api/templates/<template_id>/generate` - Generate document from template

### Health (Public)
- `GET /` - API info
- `GET /health` - Health check

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
FLASK_ENV=development              # development, testing, production
FLASK_DEBUG=False                  # Never true in production
SECRET_KEY=<min-32-chars>         # Flask session key (CHANGE!)
JWT_SECRET_KEY=<min-32-chars>     # JWT signing key (CHANGE!)
DATABASE_URL=sqlite:///vincent.db # Production: PostgreSQL URI
CORS_ORIGINS=http://localhost:3000 # Comma-separated list
RATE_LIMIT_ENABLED=True           # Enable endpoint rate limiting
AUTH_ENABLED=True                 # Require authentication
```

## Development

### Testing
```bash
# Run all tests
pytest tests/

# With coverage report
pytest --cov=app tests/

# Specific test file
pytest tests/test_auth.py -v
```

### Code Quality
```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/

# Sort imports
isort app/ tests/
```

## Deployment

### Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 30 run:app
```

## Security Checklist

Before production deployment, verify:

- [ ] Strong, unique SECRET_KEY and JWT_SECRET_KEY (min 32 chars)
- [ ] Database password changed
- [ ] CORS_ORIGINS restricted to your domains
- [ ] HTTPS/TLS enabled and HSTS enforced
- [ ] Running behind reverse proxy (nginx, CloudFront)
- [ ] Using Gunicorn (not Flask dev server)
- [ ] Health checks passing
- [ ] Logging and monitoring configured
- [ ] Database backups enabled
- [ ] Firewall rules configured
- [ ] All tests passing

See [SECURITY.md](SECURITY.md) for detailed security information.  
See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for pre-deployment verification.

## What's New in v2.0

### Security
- ✨ JWT-based authentication (was: no auth)
- ✨ Role-based access control (was: open API)
- ✨ Input validation with Pydantic (was: raw input)
- ✨ HTML escaping for XSS prevention (was: vulnerable)
- ✨ Rate limiting on all endpoints (was: unprotected)
- ✨ Comprehensive security headers (was: missing)
- ✨ Audit logging for all actions (was: minimal logging)

### Quality
- ✨ Error handling middleware (was: generic errors)
- ✨ Structured logging with rotation (was: debug only)
- ✨ Pydantic request schemas (was: no validation)
- ✨ Environment-based configuration (was: hardcoded)
- ✨ Comprehensive test suite (was: no tests)
- ✨ Docker/docker-compose (was: development only)

### Reliability
- ✨ Database optimizations (indices, lazy loading)
- ✨ Connection pooling and timeouts
- ✨ Transaction management
- ✨ Health check endpoints
- ✨ Production WSGI server (Gunicorn)

## Support

**Security Issues**: Please email security@yourdomain.com (do not use GitHub issues)

**General Issues**: https://github.com/Hyperspace-Entity/Vincent-fullstack/issues

**Documentation**: See [SECURITY.md](SECURITY.md) and [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

## License

MIT
