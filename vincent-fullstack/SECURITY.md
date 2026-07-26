# Security-First Production Refactor of Vincent Backend

## Overview

Vincent has been transformed from a prototype into production-grade, security-hardened code following industry best practices and OWASP guidelines.

## Key Improvements

### 🔐 Authentication & Authorization
- **JWT-based authentication** with secure token generation and validation
- **Role-Based Access Control (RBAC)** with three roles: Admin, Reviewer, Automation
- **Password hashing** using PBKDF2-SHA256 with 16-byte salt
- **Token refresh mechanism** with separate access/refresh tokens
- **Rate limiting** on auth endpoints (5/hour registration, 10/minute login)

### ✅ Input Validation & Security
- **Pydantic schemas** for all request payloads
- **HTML escaping** on all user inputs to prevent XSS
- **Whitelist validation** for document types, statuses, and severity levels
- **Request size limits** (16MB max by default)
- **String length limits** on all fields

### 📝 Logging & Audit Trail
- **Structured security logging** for all auth attempts and actions
- **Audit entries** for document lifecycle events
- **User tracking** for all document operations
- **Rotating file handlers** with 10x10MB backup files
- **Log levels** configurable via environment variables

### 🚨 Rate Limiting
- **Endpoint-specific limits**: 100/hour for list/detail, 50/hour for approvals, 20/hour for bulk operations
- **Auth-specific limits**: 5/hour registration, 10/minute login attempts
- **IP-based throttling** via Flask-Limiter

### 🔒 Security Headers
- **HSTS** (Strict-Transport-Security) with 1-year max-age
- **CSP** (Content-Security-Policy) restricting to 'self'
- **X-Frame-Options: DENY** prevents clickjacking
- **X-Content-Type-Options: nosniff** prevents MIME sniffing
- **Referrer-Policy** set to strict-origin-when-cross-origin

### 🌐 CORS Configuration
- **Configurable origins** via CORS_ORIGINS environment variable
- **Restricted HTTP methods** (GET, POST, PATCH, DELETE, OPTIONS)
- **Credentials support** with SameSite=Lax
- **Max-age caching** of 3600 seconds

### 🗄️ Database Security
- **SQLAlchemy ORM** prevents SQL injection (parameterized queries)
- **Connection pooling** with security options
- **Transaction isolation** at SQLAlchemy level
- **Foreign key constraints** for referential integrity
- **Cascading deletes** for related records

### 🐳 Deployment
- **Docker support** with non-root user (UID 1000)
- **docker-compose** with PostgreSQL service
- **Gunicorn WSGI server** (never Flask debug server in production)
- **Health checks** on all services
- **Volume mounts** for persistent logs

### 📦 Dependencies
- **Updated versions** with security patches
- **Locked versions** for reproducibility
- **Development and production** dependency separation
- **Removed debug dependencies** from production

## Setup Instructions

### Development

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env
# Edit .env with your values (at minimum, change SECRET_KEY and JWT_SECRET_KEY)

# 4. Run application
python run.py

# 5. Test
curl http://localhost:5000/health
```

### Production with Docker

```bash
# 1. Create .env file with production values
cp .env.example .env.production
# Edit with strong secrets and real database credentials

# 2. Build and run
docker-compose -f docker-compose.yml up -d

# 3. Verify
curl http://localhost:8000/health
```

## API Endpoints

### Authentication

**Register User**
```bash
POST /auth/register
Content-Type: application/json

{
  "username": "reviewer1",
  "email": "reviewer@example.com",
  "password": "SecurePass123",
  "roles": ["reviewer"]
}
```

**Login**
```bash
POST /auth/login
Content-Type: application/json

{
  "username": "reviewer1",
  "password": "SecurePass123"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Refresh Token**
```bash
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

**Get Current User**
```bash
GET /auth/me
Authorization: Bearer <access_token>
```

### Documents

**Create Document**
```bash
POST /api/queue
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "Invoice ABC123",
  "content": "Document content...",
  "doc_type": "invoice",
  "source": "automation",
  "extracted_fields": {"amount": "$1000"},
  "extraction_confidence": {"amount": 0.95}
}
```

**List Documents**
```bash
GET /api/queue?status=pending&sort=risk&skip=0&limit=50
Authorization: Bearer <access_token>
```

**Get Document**
```bash
GET /api/queue/<doc_id>
Authorization: Bearer <access_token>
```

**Update Document**
```bash
PATCH /api/queue/<doc_id>
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "Updated Title",
  "content": "Updated content"
}
```

**Approve Document**
```bash
POST /api/queue/<doc_id>/approve
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "notes": "Approved after review"
}
```

**Reject Document**
```bash
POST /api/queue/<doc_id>/reject
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "notes": "Missing required fields"
}
```

**Bulk Approve**
```bash
POST /api/queue/bulk-approve
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "document_ids": ["doc1", "doc2", "doc3"],
  "max_risk": "low",
  "notes": "Batch approval"
}
```

## Security Best Practices

### Environment Variables

Never commit `.env` to version control. Always:
- Generate cryptographically secure secrets (min 32 chars)
- Use strong passwords (uppercase, lowercase, digits, symbols)
- Rotate secrets regularly
- Use different secrets for each environment
- Store in secure secret management (AWS Secrets Manager, HashiCorp Vault, etc.)

### Database

- Always use strong, randomly generated passwords
- Restrict database access by IP/security group
- Use TLS for database connections in production
- Enable database encryption at rest
- Regular backups with encryption
- Implement database activity monitoring

### API Security

- Always use HTTPS in production (enforce via HSTS header)
- Keep JWT tokens short-lived (1 hour access tokens)
- Use refresh tokens for long-term access (30 days)
- Implement token rotation
- Monitor for suspicious activity (failed logins, bulk operations)
- Rate limit all endpoints

### Deployment

- Run behind a reverse proxy (nginx, CloudFront, etc.)
- Use Web Application Firewall (WAF)
- Monitor logs for security events
- Set up alerts for rate limit breaches
- Implement DDoS protection
- Use managed services where possible (RDS, managed databases)

## Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=app tests/

# Specific test file
pytest tests/test_auth.py
```

## Monitoring & Alerts

Log files are stored in `logs/vincent.log`. Monitor for:
- Failed authentication attempts
- Authorization failures
- Rate limit breaches
- Database errors
- Bulk operations
- Unusual access patterns

## Compliance

This implementation addresses:
- **OWASP Top 10**: A01 (Broken Access Control), A02 (Cryptographic Failures), A03 (Injection), A07 (XSS), A09 (Logging & Monitoring)
- **CWE**: CWE-200, CWE-287, CWE-331, CWE-352, CWE-434, CWE-522, CWE-613, CWE-1021
- **NIST**: Secure coding practices and authentication standards

## Migration from v1.x

If migrating from the original Vincent prototype:

1. **Database**: Export data from old SQLite database
2. **Users**: Create user accounts in new system
3. **Documents**: Import documents using the new API with proper authentication
4. **Templates**: Recreate templates in new system
5. **Testing**: Thoroughly test before production cutover

## Support & Issues

For security issues, please email security@yourdomain.com instead of using GitHub issues.

For general issues: https://github.com/Hyperspace-Entity/Vincent-fullstack/issues
