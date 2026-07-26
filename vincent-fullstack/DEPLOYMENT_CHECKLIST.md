# Vincent Review Queue - Deployment Security Checklist

## Pre-Deployment

- [ ] All environment variables set with strong, random values (min 32 chars)
- [ ] Database credentials changed from defaults
- [ ] Debug mode disabled (`FLASK_DEBUG=False`)
- [ ] CORS_ORIGINS restricted to known domains only
- [ ] Logging configured and tested
- [ ] Database backups configured
- [ ] SSL/TLS certificate obtained and installed
- [ ] Firewall rules configured
- [ ] Security headers validated in browser dev tools

## Database

- [ ] Database running on private network (not exposed to internet)
- [ ] Database password changed from installation defaults
- [ ] Database backups enabled with encryption
- [ ] Database activity monitoring enabled
- [ ] Regular backup restoration tests scheduled
- [ ] Database user has minimal required permissions
- [ ] Connection requires TLS/SSL

## Application

- [ ] Running behind reverse proxy (nginx/CloudFront/etc)
- [ ] Using Gunicorn or similar WSGI server (not Flask dev server)
- [ ] Workers configured appropriately for load (4-8 for typical usage)
- [ ] Timeouts set appropriately (30-60s)
- [ ] Access logs enabled and monitored
- [ ] Error logs monitored for exceptions
- [ ] Application running as non-root user
- [ ] File permissions restricted appropriately

## Security

- [ ] HTTPS enforced (HSTS header present)
- [ ] CORS restrictions tested
- [ ] Rate limiting verified on all endpoints
- [ ] Authentication required on all protected endpoints
- [ ] Role-based access control tested
- [ ] Input validation tested with malicious payloads
- [ ] XSS protection verified (HTML escaping)
- [ ] CSRF protection in place (if applicable)
- [ ] Security headers present and correct

## Monitoring & Alerting

- [ ] Log aggregation configured (ELK, CloudWatch, etc)
- [ ] Alerts set for failed login attempts
- [ ] Alerts set for rate limit breaches
- [ ] Alerts set for database errors
- [ ] Alerts set for application crashes
- [ ] Alerts set for unusual bulk operations
- [ ] Performance monitoring enabled
- [ ] Uptime monitoring enabled

## Incident Response

- [ ] Security incident response plan documented
- [ ] Contact information for security team
- [ ] Process for revoking compromised tokens
- [ ] Process for rotating secrets
- [ ] Backup restoration procedure tested
- [ ] DDoS mitigation plan in place

## Compliance & Audit

- [ ] Security audit completed
- [ ] Penetration testing completed
- [ ] Compliance requirements identified and addressed
- [ ] Audit logging enabled
- [ ] Audit logs protected from tampering
- [ ] Privacy policy reviewed and updated
- [ ] Data retention policy implemented

## Post-Deployment

- [ ] Production environment validated
- [ ] Health checks passing
- [ ] API endpoints tested
- [ ] Authentication flow tested end-to-end
- [ ] User access verified
- [ ] Performance acceptable
- [ ] Monitoring dashboards accessible
- [ ] Incident response team trained
