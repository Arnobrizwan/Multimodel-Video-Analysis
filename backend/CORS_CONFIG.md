# CORS Configuration Guide

## Overview

The API uses a secure, environment-aware CORS configuration that prevents the critical security vulnerability of allowing wildcard origins (`*`) with credentials.

## Security Issue Fixed

**Before (CRITICAL VULNERABILITY)**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Allows ANY website
    allow_credentials=True,  # ❌ With credentials!
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Problem**: This allows ANY malicious website to make authenticated requests to your API, stealing user data and sessions.

**After (SECURE)**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # ✅ Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ Specific methods
    allow_headers=["Content-Type", "Authorization"],  # ✅ Specific headers
    max_age=600,
)
```

## Configuration

### Development Mode (Default)

When `CORS_ORIGINS` is not set, development origins are automatically allowed:

```python
[
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",  # React/Next.js default
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]
```

### Production Mode

Set `CORS_ORIGINS` in your `.env` file:

```bash
# Single origin
CORS_ORIGINS=https://yourdomain.com

# Multiple origins (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://app.yourdomain.com
```

## Security Properties

### ✅ Protected Against

1. **Cross-Site Request Forgery (CSRF)**
   - Only configured origins can make requests
   - Credentials tied to specific origins

2. **Data Theft**
   - Malicious sites cannot read responses
   - Authentication tokens protected

3. **Session Hijacking**
   - Cookies/credentials only sent to allowed origins

### ❌ NOT Protected If

1. **Wildcard with Credentials**
   ```python
   allow_origins=["*"], allow_credentials=True  # NEVER DO THIS
   ```

2. **Overly Broad Origins**
   ```bash
   CORS_ORIGINS=http://*  # Don't use wildcards
   ```

## Environment Variables

Add to `.env`:

```bash
# Development (leave empty)
CORS_ORIGINS=

# Staging
CORS_ORIGINS=https://staging.yourdomain.com

# Production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Frontend Configuration

### React/Vite

**Development** (`vite.config.js`):
```javascript
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
```

**Production**: Set API URL to your domain with HTTPS.

### Vercel Deployment

Add environment variable in Vercel dashboard:
```
CORS_ORIGINS=https://yourapp.vercel.app
```

## Testing

### Test CORS Headers

```bash
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8000/process_video -v
```

Expected response headers:
```
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS
access-control-allow-headers: Content-Type, Authorization
access-control-max-age: 600
```

### Test Unauthorized Origin

```bash
curl -H "Origin: https://evil.com" \
     http://localhost:8000/ -v
```

Should NOT include `access-control-allow-origin: https://evil.com`

## Troubleshooting

### Error: "No 'Access-Control-Allow-Origin' header"

**Cause**: Frontend origin not in allowed list

**Solution**:
1. Check `.env` has correct `CORS_ORIGINS`
2. Restart backend after changing `.env`
3. Verify frontend URL matches exactly (http/https, port)

### Error: "Credentials mode requires exact origin"

**Cause**: Cannot use wildcard with credentials

**Solution**: Already fixed - we use specific origins only

### CORS works in dev but not production

**Checklist**:
- [ ] `CORS_ORIGINS` set in production environment
- [ ] URLs use HTTPS in production
- [ ] No trailing slashes in origin URLs
- [ ] Port matches if non-standard

## Migration Guide

### From Wildcard to Specific Origins

1. **Before deployment**, add to `.env`:
   ```bash
   CORS_ORIGINS=https://your-frontend.com
   ```

2. **Test locally** with production config:
   ```bash
   CORS_ORIGINS=http://localhost:5173 python main.py
   ```

3. **Deploy** and verify:
   ```bash
   curl -H "Origin: https://your-frontend.com" https://api.yourdomain.com/health -v
   ```

## Best Practices

1. ✅ **Always use HTTPS in production**
   ```bash
   CORS_ORIGINS=https://app.com  # ✅ Secure
   CORS_ORIGINS=http://app.com   # ❌ Insecure
   ```

2. ✅ **Specific origins only**
   ```bash
   CORS_ORIGINS=https://app.com,https://www.app.com  # ✅ Good
   CORS_ORIGINS=*  # ❌ Never
   ```

3. ✅ **Keep list minimal**
   - Only add origins you control
   - Remove unused origins

4. ✅ **Review regularly**
   - Audit allowed origins quarterly
   - Remove old/deprecated domains

## References

- [MDN CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [OWASP CORS Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [FastAPI CORS Middleware](https://fastapi.tiangolo.com/tutorial/cors/)

## Security Audit

Last reviewed: 2025-01-10

- [x] Wildcard origins removed
- [x] Environment-based configuration
- [x] Specific methods only
- [x] Specific headers only
- [x] HTTPS enforced for production
- [x] Tests added
- [x] Documentation updated
