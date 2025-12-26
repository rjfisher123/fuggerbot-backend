# FuggerBot Deployment Guide

This guide covers deploying FuggerBot using Docker and Fly.io.

## Prerequisites

- Docker installed and running
- (Optional) Fly.io CLI installed (`flyctl`)

## Local Docker Deployment

### Build the Docker image

```bash
docker build -t fuggerbot:latest .
```

### Run the container

```bash
docker run -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -e PORT=8080 \
  fuggerbot:latest
```

Or use docker-compose:

```bash
docker-compose up
```

### Verify deployment

```bash
curl http://localhost:8080/health
curl http://localhost:8080/
```

## Fly.io Deployment

### Initial setup

1. Install Fly.io CLI: https://fly.io/docs/getting-started/installing-flyctl/

2. Login to Fly.io:
```bash
flyctl auth login
```

3. Create a new app (if not already created):
```bash
flyctl apps create fuggerbot
```

4. Set environment variables:
```bash
flyctl secrets set JWT_SECRET_KEY=your-secret-key-here
flyctl secrets set TWILIO_SID=your_twilio_sid
flyctl secrets set TWILIO_AUTH=your_twilio_auth
# ... other secrets
```

5. Deploy:
```bash
flyctl deploy
```

### View logs

```bash
flyctl logs
```

### Scale the app

```bash
flyctl scale count 1
flyctl scale vm shared-cpu-1x --memory 512
```

## Environment Variables

Required environment variables (set via Fly.io secrets or Docker environment):

- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `TWILIO_SID`: Twilio account SID (optional)
- `TWILIO_AUTH`: Twilio auth token (optional)
- `GEMINI_API_KEY`: Google Gemini API key (optional)
- `IBKR_HOST`: IBKR host (default: 127.0.0.1)
- `IBKR_PORT`: IBKR port (default: 7496)
- `IBKR_PAPER_PORT`: IBKR paper trading port (default: 7497)

## Health Check

The application includes a health check endpoint at `/health`:

```bash
curl https://your-app.fly.dev/health
```

## Port Configuration

The application runs on port 8080 by default. This can be changed via the `PORT` environment variable.

## Data Persistence

For production deployments, consider:
- Using Fly.io volumes for persistent data
- Setting up a managed database (PostgreSQL) instead of SQLite
- Using object storage for forecast snapshots

## Troubleshooting

### Container won't start

1. Check logs: `docker logs <container_id>` or `flyctl logs`
2. Verify port 8080 is accessible
3. Check environment variables are set correctly

### Health check fails

1. Ensure the app is listening on 0.0.0.0:8080
2. Check firewall/security group settings
3. Verify the `/health` endpoint is accessible











